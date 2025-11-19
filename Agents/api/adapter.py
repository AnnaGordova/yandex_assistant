import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from Agents.nlp_agent.agent_ws import Agent_nlp
from Agents.web_agent.agent import get_agents, run_agent
from Agents.api.utils import candidates_to_products  # твоя функция-обёртка над get_saved_candidates()

logger = logging.getLogger("adapter")

if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


# ---- session state ----

@dataclass
class AdapterSession:
    token: str
    items: List[Dict[str, Any]] = field(default_factory=list)   # план вещей от NLP
    current_item_index: Optional[int] = None                    # какая вещь сейчас в работе


def _build_system_prompt_from_params(params: Dict[str, Any]) -> str:
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
    dialog: List[Dict[str, str]] = []

    params = message_request.get("params") or {}
    sys_prompt = _build_system_prompt_from_params(params)
    if sys_prompt:
        dialog.append({"role": "system", "content": sys_prompt})

    chat_history = message_request.get("chatHistory") or []
    for turn in chat_history:
        text = turn.get("text") or turn.get("Text") or ""
        if not text:
            continue
        is_user = bool(turn.get("isUser") or turn.get("IsUser"))
        role = "user" if is_user else "assistant"
        dialog.append({"role": role, "content": text})

    msg = (message_request.get("message") or "").strip()
    if msg:
        if not chat_history or chat_history[-1].get("text") != msg:
            dialog.append({"role": "user", "content": msg})

    return dialog


def _history_to_web_text(message_request: Dict[str, Any]) -> str:
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


def _safe_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return repr(obj)


class Adapter:
    """
    Адаптер между:
      - MessageRequest (Go)
      - NLP-агентом
      - Web-агентом
      - MessageAnswer (Go)
    """

    def __init__(self) -> None:
        logger.info("Initializing Adapter...")

        self.nlp_agent = Agent_nlp()
        logger.info("NLP agent initialized")

        self.web_assistant, self.web_agent = get_agents(show_browser=False)
        logger.info("Web agent initialized")

        # сессии по token
        self.sessions: Dict[str, AdapterSession] = {}

        logger.info("Adapter initialized successfully")

    # ---- session helpers ----

    def _get_session(self, token: str) -> AdapterSession:
        if not token:
            token = "_anonymous"
        session = self.sessions.get(token)
        if session is None:
            session = AdapterSession(token=token)
            self.sessions[token] = session
        return session

    # ---- main entry ----

    def process_message_request(self, message_request: Dict[str, Any]) -> Dict[str, Any]:
        email = message_request.get("email") or ""
        token = message_request.get("token") or ""
        short_token = token[:8] + "..." if token else ""

        session = self._get_session(token)

        msg_raw = (message_request.get("message") or "").strip()

        logger.info(
            "Received MessageRequest: email=%s token=%s message=%r",
            email,
            short_token,
            msg_raw[:200],
        )

        try:
            # ----------------- 0. спец-команда: next_item -----------------
            if msg_raw == "next_item" and session.items and session.current_item_index is not None:
                # отдельная функция уже возвращает готовый MessageAnswer
                return self._handle_next_item(message_request, session)

            # (сюда же можно потом добавить обработку like:/dislike:, но пока не трогаем)

            # ----------------- 1. запускаем NLP -----------------
            dialog = _history_to_nlp_dialog(message_request)
            logger.debug("Built NLP dialog with %d turns", len(dialog))

            nlp_result = self._run_nlp(dialog)
            logger.debug("NLP result raw: %s", _safe_json(nlp_result))

            status = (nlp_result.get("status") or "ok").lower()
            items = nlp_result.get("items") or []

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

            # ----------------- 2. только вопросы → сразу ответ -----------------
            if status == "questions":
                logger.info("NLP requests clarification questions, no web search yet")
                return {
                    "message": nlp_text or "Нужны уточнения, чтобы подобрать товары.",
                    "products": [],
                    "buttons": [],
                }

            # дальше во всех ветках мы будем вычислять web_text,
            # а в конце — ОДИН раз собирать MessageAnswer.
            history_text = _history_to_web_text(message_request)
            web_text = ""

            # ----------------- 3. режим уточнения текущей вещи -----------------
            if status == "ok" and items and session.items and session.current_item_index is not None:
                logger.info(
                    "NLP returned items while plan already exists — treating as refinement "
                    "for current item #%d/%d",
                    session.current_item_index + 1,
                    len(session.items),
                )

                # Берём только первую вещь из нового результата как уточнённое описание
                new_item = items[0]
                session.items[session.current_item_index] = new_item

                web_text = self._run_web_for_current_item(session, history_text)

            # ----------------- 4. новый план из нескольких вещей -----------------
            elif status == "ok" and items:
                logger.info("NLP returned new items list, starting with first item only")

                session.items = items
                session.current_item_index = 0

                web_text = self._run_web_for_current_item(session, history_text)

            # ----------------- 5. одиночный запрос (без плана) -----------------
            else:
                logger.info("NLP requests single web search (status=%s)", status)
                web_text = self._run_web_single(nlp_result, message_request, history_text)

                # сбрасываем план, если был
                session.items = []
                session.current_item_index = None

            # ----------------- 6. общий хвост: достаём продукты и собираем ответ -----------------
            # ВАЖНО: сюда приходим из ВСЕХ веток 3–5, поэтому метод ВСЕГДА что-то возвращает.
            products = candidates_to_products()  # clear=True внутри utils
            logger.info("Collected %d products from web_agent", len(products))

            final_message = self._build_final_message(nlp_text, web_text, products, session)
            buttons = self._build_buttons_for_products(products, session)

            answer = {
                "message": final_message,
                "products": products,
                "buttons": buttons,
            }

            logger.debug("Final MessageAnswer: %s", _safe_json(answer))
            return answer

        except Exception as e:
            logger.exception("Error in Adapter.process_message_request: %s", e)
            # fallback-ответ, чтобы ws-сервер НИКОГДА не отправлял null
            return {
                "message": "Произошла внутренняя ошибка при обработке запроса.",
                "products": [],
                "buttons": [],
            }


    # ---- NLP ----

    def _run_nlp(self, dialog: List[Dict[str, str]]) -> Dict[str, Any]:
        logger.info("Calling NLP agent with %d dialog turns", len(dialog))
        result = self.nlp_agent.process_dialog(dialog)
        if not isinstance(result, dict):
            logger.warning("NLP agent returned non-dict result, wrapping into dict")
            result = {"status": "ok", "answer": str(result)}
        return result

    # ---- Web: одиночный запрос ----

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

    # ---- Web: текущая вещь из плана ----

    def _run_web_for_current_item(self, session: AdapterSession, history_text: str) -> str:
        assert session.items and session.current_item_index is not None
        idx = session.current_item_index
        item = session.items[idx]

        web_prompt = (
            item.get("query")
            or item.get("prompt")
            or item.get("title")
            or ""
        )
        if not web_prompt:
            web_prompt = (
                "Найди подходящий товар по описанию: "
                + json.dumps(item, ensure_ascii=False)
            )

        logger.info(
            "Running web_agent for item #%d/%d: %r",
            idx + 1,
            len(session.items),
            web_prompt[:200],
        )
        logger.debug("Item #%d raw: %s", idx + 1, _safe_json(item))
        logger.debug("Web history_text:\n%s", history_text)

        web_text = run_agent(
            user_query=web_prompt,
            history_text=history_text,
        )

        logger.info("Web_agent finished search for item #%d", idx + 1)
        logger.debug(
            "Web_agent result for item #%d (truncated): %r",
            idx + 1,
            web_text[:500],
        )
        return web_text

    # ---- переход к следующей вещи ----

    def _handle_next_item(
        self,
        message_request: Dict[str, Any],
        session: AdapterSession,
    ) -> Dict[str, Any]:
        """
        Обрабатывает message == 'next_item':
        переключается на следующую вещь из session.items и запускает web-агента только по ней.
        """
        if session.current_item_index is None or not session.items:
            logger.info("next_item received but no items in session")
            return {
                "message": "Список вещей для подбора пуст. Начнём сначала — опишите, что хотите купить.",
                "products": [],
                "buttons": [],
            }

        if session.current_item_index >= len(session.items) - 1:
            logger.info("next_item received but already at last item")
            return {
                "message": "Мы уже подобрали товары по всем запланированным вещам 👌",
                "products": [],
                "buttons": [],
            }

        session.current_item_index += 1
        logger.info(
            "Switching to next item: #%d/%d",
            session.current_item_index + 1,
            len(session.items),
        )

        history_text = _history_to_web_text(message_request)
        web_text = self._run_web_for_current_item(session, history_text)

        products = candidates_to_products()
        logger.info("Collected %d products for next item", len(products))

        final_message = self._build_final_message("", web_text, products, session)
        buttons = self._build_buttons_for_products(products, session)

        answer = {
            "message": final_message,
            "products": products,
            "buttons": buttons,
        }
        logger.debug("MessageAnswer (next_item): %s", _safe_json(answer))
        return answer

    # ---- финальный текст и кнопки ----

    def _build_final_message(
        self,
        nlp_text: str,
        web_text: str,
        products: List[Dict[str, Any]],
        session: AdapterSession,
    ) -> str:
        parts: List[str] = []

        if nlp_text:
            parts.append(nlp_text.strip())

        # если есть несколько вещей — подчеркнём, для какой сейчас подбор
        if session.items and session.current_item_index is not None:
            idx = session.current_item_index
            cur = session.items[idx]
            title = cur.get("title") or cur.get("web_prompt") or cur.get("prompt") or ""
            if title:
                parts.append(f"Сейчас подбираем варианты для вещи №{idx + 1}: {title}")
            else:
                parts.append(f"Сейчас подбираем варианты для вещи №{idx + 1} из списка.")

        if products:
            parts.append(f"Я подобрал {len(products)} вариантов, вот они ниже 👇")
            if (
                session.items
                and session.current_item_index is not None
                and session.current_item_index < len(session.items) - 1
            ):
                parts.append(
                    "Когда будете готовы перейти к следующей вещи, нажмите кнопку "
                    "«Следующая вещь» или отправьте команду next_item."
                )
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
        self,
        products: List[Dict[str, Any]],
        session: AdapterSession,
    ) -> List[Dict[str, str]]:
        buttons: List[Dict[str, str]] = []

        for i, p in enumerate(products, start=1):
            pid = p.get("id", i)
            buttons.append(
                {
                    "text": f"👍 Товар {i}",
                    "value": f"like:{pid}",
                }
            )
            buttons.append(
                {
                    "text": f"👎 Товар {i}",
                    "value": f"dislike:{pid}",
                }
            )

        # если есть ещё вещи в плане — добавляем кнопку перехода к следующей
        if (
            session.items
            and session.current_item_index is not None
            and session.current_item_index < len(session.items) - 1
        ):
            buttons.append(
                {
                    "text": "➡️ Следующая вещь",
                    "value": "next_item",
                }
            )

        logger.debug(
            "Built %d buttons for %d products (items_in_plan=%d, current_index=%s)",
            len(buttons),
            len(products),
            len(session.items),
            session.current_item_index,
        )
        return buttons


if __name__ == "__main__":
    import sys

    logger.setLevel(logging.DEBUG)

    raw = sys.stdin.read()
    if not raw.strip():
        print("[]")
        raise SystemExit(0)

    try:
        req = json.loads(raw)
    except Exception as e:
        logger.error("Failed to parse stdin JSON: %s", e)
        print(
            json.dumps(
                {"message": "Bad JSON", "products": [], "buttons": []},
                ensure_ascii=False,
            )
        )
        raise SystemExit(1)

    adapter = Adapter()
    ans = adapter.process_message_request(req)
    print(json.dumps(ans, ensure_ascii=False))
