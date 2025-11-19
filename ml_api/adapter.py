# adapter.py
import json
import logging
from typing import Any, Dict, List

from Agent_NLP.agent_ws import Agent_nlp
from web_agent.agent import get_agents, run_agent
from utils import candidates_to_products  # твоя функция-обёртка над get_saved_candidates()

# --------------------------------------------------------------------
# Логгер
# --------------------------------------------------------------------

logger = logging.getLogger("adapter")

# Если модуль запустили как скрипт — настроим простой вывод в консоль.
# Внутри сервиса можно переконфигурировать логгер снаружи.
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# --------------------------------------------------------------------
# Вспомогательные функции
# --------------------------------------------------------------------


def _build_system_prompt_from_params(params: Dict[str, Any]) -> str:
    """
    Делаем аккуратный system-подсказчик для NLP-агента из MessageParams.
    """
    if not params:
        return ""

    parts: List[str] = []
    address = params.get("address") or params.get("Address")
    budget = params.get("budget") or params.get("Budget")
    wishes = params.get("wishes") or params.get("Wishes")

    if address:
        parts.append(f"Адрес/регион пользователя: {address}.")
    if budget:
        parts.append(f"Бюджет пользователя: {budget}.")
    if wishes:
        parts.append(f"Пожелания пользователя: {wishes}.")

    if not parts:
        return ""

    return (
        "Контекст от бэкенда (не задавай эти вопросы заново, а используй как факты): "
        + " ".join(parts)
    )


def _history_to_nlp_dialog(message_request: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Преобразует MessageRequest из Go в формат диалога для NLP-агента.
    """
    dialog: List[Dict[str, str]] = []

    # 1) system-контекст с address/budget/wishes
    params = message_request.get("params") or {}
    sys_prompt = _build_system_prompt_from_params(params)
    if sys_prompt:
        dialog.append({"role": "system", "content": sys_prompt})

    # 2) история чата
    chat_history = message_request.get("chatHistory") or []
    for turn in chat_history:
        text = turn.get("text") or turn.get("Text") or ""
        if not text:
            continue
        is_user = bool(turn.get("isUser") or turn.get("IsUser"))
        role = "user" if is_user else "assistant"
        dialog.append({"role": role, "content": text})

    # 3) текущее сообщение (на всякий случай)
    msg = (message_request.get("message") or "").strip()
    if msg:
        # если история пуста или последнее сообщение в истории другое — добавим
        if not chat_history or chat_history[-1].get("text") != msg:
            dialog.append({"role": "user", "content": msg})

    return dialog


def _history_to_web_text(message_request: Dict[str, Any]) -> str:
    """
    Текстовая история для web-агента. Можно без ролей, просто контекст.
    """
    parts: List[str] = []
    chat_history = message_request.get("chatHistory") or []
    for turn in chat_history:
        text = turn.get("text") or turn.get("Text") or ""
        if text:
            parts.append(text)

    msg = (message_request.get("message") or "").strip()
    if msg:
        parts.append(msg)

    return "\n".join(parts)


# --------------------------------------------------------------------
# Основной адаптер
# --------------------------------------------------------------------


class Adapter:
    """
    Адаптер между:
      - Go MessageRequest
      - NLP-агентом (диалог/планировщик)
      - web-агентом (поиск по маркетплейсу)
      - Go MessageAnswer (message + products + buttons)
    """

    def __init__(self) -> None:
        logger.info("Initializing Adapter...")

        # NLP-агент
        self.nlp_agent = Agent_nlp()
        logger.info("NLP agent initialized")

        # web-агент (assistant + agent для computer-use)
        self.web_assistant, self.web_agent = get_agents(show_browser=True)
        logger.info("Web agent initialized")

        logger.info("Adapter initialized successfully")

    # ------------------------ Публичный API -------------------------

    def process_message_request(self, message_request: Dict[str, Any]) -> Dict[str, Any]:
        """
        Главная точка входа: принимает MessageRequest (JSON от Go),
        возвращает MessageAnswer.
        """
        email = message_request.get("email") or ""
        token = message_request.get("token") or ""
        short_token = token[:8] + "..." if token else ""

        logger.info(
            "Received MessageRequest: email=%s token=%s message=%r",
            email,
            short_token,
            (message_request.get("message") or "")[:200],
        )

        try:
            dialog = _history_to_nlp_dialog(message_request)
            logger.debug("Built NLP dialog with %d turns", len(dialog))

            # --- шаг 1: NLP-агент ---
            nlp_result = self._run_nlp(dialog)
            logger.debug("NLP result raw: %s", _safe_json(nlp_result))

            status = (nlp_result.get("status") or "ok").lower()
            items = nlp_result.get("items") or []

            # Текст, который NLP хочет показать пользователю прямо сейчас
            nlp_text = (
                nlp_result.get("questions")
                or nlp_result.get("answer")
                or nlp_result.get("message")
                or ""
            )

            logger.info(
                "NLP status=%s, items_count=%d, has_text=%s",
                status,
                len(items),
                bool(nlp_text),
            )

            # --- режим только вопросов (ещё рано идти в web) ---
            if status == "questions":
                logger.info("NLP requests clarification questions, no web search yet")
                return {
                    "message": nlp_text or "Нужны уточнения, чтобы подобрать товары.",
                    "products": [],
                    "buttons": [],
                }

            # --- режим: уже есть список вещей, нужно идти в web по каждой ---
            history_text = _history_to_web_text(message_request)

            if status == "ok" and items:
                logger.info("NLP returned items list, running web search for each item")
                web_text = self._run_web_for_items(items, history_text)
            else:
                # fallback: одиночный запрос в web-агент
                logger.info("NLP requests single web search (status=%s)", status)
                web_text = self._run_web_single(nlp_result, message_request, history_text)

            # --- после web-агента: достаём все сохранённые кандидаты ---
            products = candidates_to_products()
            logger.info("Collected %d products from web_agent", len(products))

            # Финальный текст для пользователя
            final_message = self._build_final_message(nlp_text, web_text, products)

            buttons = self._build_buttons_for_products(products)

            answer = {
                "message": final_message,
                "products": products,
                "buttons": buttons,
            }

            logger.debug("Final MessageAnswer: %s", _safe_json(answer))
            return answer

        except Exception as e:
            logger.exception("Error in Adapter.process_message_request: %s", e)
            # fallback-ответ, чтобы Go не падал на пустом ответе
            return {
                "message": "Произошла внутренняя ошибка при обработке запроса.",
                "products": [],
                "buttons": [],
            }

    # ------------------------ Внутреннее: NLP -------------------------

    def _run_nlp(self, dialog: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Обёртка над NLP-агентом с логированием.
        Предполагается интерфейс Agent_nlp.process_dialog(dialog) -> dict.
        """
        logger.info("Calling NLP agent with %d dialog turns", len(dialog))
        result = self.nlp_agent.process_dialog(dialog)
        if not isinstance(result, dict):
            logger.warning("NLP agent returned non-dict result, wrapping into dict")
            result = {"status": "ok", "answer": str(result)}
        return result

    # ------------------------ Внутреннее: Web -------------------------

    def _run_web_single(
        self,
        nlp_result: Dict[str, Any],
        message_request: Dict[str, Any],
        history_text: str,
    ) -> str:
        """
        Одиночный вызов web-агента. Берём web_prompt из nlp_result
        или из текущего текста пользователя.
        """
        web_prompt = (
            nlp_result.get("query")
            or nlp_result.get("search_prompt")
            or nlp_result.get("final_query")
        )

        if not web_prompt:
            # fallback: последняя фраза пользователя
            web_prompt = (message_request.get("message") or "").strip()

        logger.info("Running web_agent for single query: %r", web_prompt[:200])
        logger.debug("Web history_text:\n%s", history_text)

        web_text = run_agent(
            user_query=web_prompt,
            history_text=history_text
        )

        logger.info("Web_agent finished single search")
        logger.debug("Web_agent single result text (truncated): %r", web_text[:500])
        return web_text

    def _run_web_for_items(
        self,
        items: List[Dict[str, Any]],
        history_text: str,
    ) -> str:
        """
        Обрабатывает ВСЕ items из NLP-агента:
        для каждой вещи формирует промпт и вызывает web-агента.
        Возвращает склеенный текстовый отчёт.
        """
        blocks: List[str] = []

        for idx, item in enumerate(items, start=1):
            web_prompt = (
                item.get("query")
                or item.get("prompt")
                or item.get("title")
                or ""
            )

            if not web_prompt:
                web_prompt = f"Найди подходящий товар по описанию: {json.dumps(item, ensure_ascii=False)}"

            logger.info("Running web_agent for item #%d: %r", idx, web_prompt[:200])
            logger.debug("Item #%d raw: %s", idx, _safe_json(item))
            logger.debug("Web history_text:\n%s", history_text)

            web_text = run_agent(
                user_query=web_prompt,
                history_text=history_text
            )

            logger.info("Web_agent finished search for item #%d", idx)
            logger.debug(
                "Web_agent result for item #%d (truncated): %r", idx, web_text[:500]
            )

            blocks.append(
                f"=== Вещь {idx} ===\n"
                f"Запрос: {web_prompt}\n\n"
                f"{web_text}\n"
            )

        return "\n\n".join(blocks)

    # ------------------------ Внутреннее: финальный ответ -------------------------

    def _build_final_message(
        self,
        nlp_text: str,
        web_text: str,
        products: List[Dict[str, Any]],
    ) -> str:
        """
        Собираем финальный текст для поля message в MessageAnswer.
        """
        parts: List[str] = []

        if nlp_text:
            parts.append(nlp_text.strip())

        if products:
            parts.append(f"Я подобрал {len(products)} вариантов, вот они ниже 👇")
        else:
            if web_text:
                parts.append("Мне не удалось сохранить товары, но вот подробности поиска:")
                parts.append(web_text.strip())
            else:
                parts.append(
                    "Пока не удалось подобрать товары. Попробуйте переформулировать запрос."
                )

        final_message = "\n\n".join(parts)
        logger.debug("Built final message (truncated): %r", final_message[:500])
        return final_message

    def _build_buttons_for_products(
        self, products: List[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """
        Базовая раскладка кнопок: для каждого товара — like/dislike.
        Фронт может использовать value как команду (например, передавать её в MessageRequest.message).
        """
        buttons: List[Dict[str, str]] = []

        for i, p in enumerate(products, start=1):
            pid = p.get("id", i)
            # Лайк — фронт пойдёт в /likeProduct с этим Product
            buttons.append(
                {
                    "text": f"👍 Товар {i}",
                    "value": f"like:{pid}",
                }
            )
            # Дизлайк — фронт пошлёт новый messageML с message="dislike:<id>"
            buttons.append(
                {
                    "text": f"👎 Товар {i}",
                    "value": f"dislike:{pid}",
                }
            )

        logger.debug("Built %d buttons for %d products", len(buttons), len(products))
        return buttons


# --------------------------------------------------------------------
# Вспомогательное для логов
# --------------------------------------------------------------------


def _safe_json(obj: Any) -> str:
    """
    Аккуратно превращает объект в JSON-строку для логов.
    """
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return repr(obj)


# --------------------------------------------------------------------
# Простой ручной запуск для локального дебага
# --------------------------------------------------------------------

if __name__ == "__main__":
    """
    Пример ручного прогона адаптера из консоли:

    echo '{"email":"test@example.com","message":"Хочу шорты и майку","token":"debug","params":{"address":"Москва","budget":"10000","wishes":"комфортно и стильно"},"chatHistory":[{"text":"Хочу шорты и майку","isUser":true}]}' | python adapter.py
    """
    import sys

    logger.setLevel(logging.DEBUG)

    raw = sys.stdin.read()
    if not raw.strip():
        print("[]")
        sys.exit(0)

    try:
        req = json.loads(raw)
    except Exception as e:
        logger.error("Failed to parse stdin JSON: %s", e)
        print(json.dumps({"message": "Bad JSON", "products": [], "buttons": []}, ensure_ascii=False))
        sys.exit(1)

    adapter = Adapter()
    ans = adapter.process_message_request(req)
    # Для локального дебага — просто печатаем JSON без \n-протокола TCP
    print(json.dumps(ans, ensure_ascii=False))