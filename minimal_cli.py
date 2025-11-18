import textwrap
from dataclasses import dataclass, field
from typing import List, Dict, Literal, Optional
from Agent_NLP.agent_ws import Agent_nlp
from web_agent.agent import get_agents, run_agent
from web_agent.web_tools import get_saved_candidates

Phase = Literal["nlp", "web"]

FLAG = False
@dataclass
class ChatMessage:
    role: str   # "user" | "assistant"
    content: str


@dataclass
class PipelineState:
    phase: Phase = "nlp"
    history: List[ChatMessage] = field(default_factory=list)
    last_nlp_result: Optional[Dict] = None


class MinimalAdapter:
    """
    Минимальный адаптер:
    - сначала гоняет сообщения в NLP-агент,
    - как только NLP говорит "готово" -> один раз запускает web-агента.
    """

    def __init__(self):
        self.state = PipelineState()
        self.nlp_agent = Agent_nlp()

        # web_assistant тебе тут особо не нужен, но get_agents прогреет браузер
        self.web_assistant, self.web_agent = get_agents(show_browser=True)

    # ---------- вспомогательные ----------

    def _history_to_dialog_for_nlp(self) -> List[Dict]:
        """Конвертация истории в формат [{role, content}] для NLP-агента."""
        return [{"role": m.role, "content": m.content} for m in self.state.history]

    def _history_to_text_for_web(self, limit: int = 10) -> str:
        """Последние N сообщений в текстовом виде для web-агента."""
        messages = self.state.history[-limit:]
        lines = []
        for m in messages:
            prefix = "Пользователь:" if m.role == "user" else "Ассистент:"
            lines.append(f"{prefix} {m.content}")
        return "\n".join(lines)

    # ---------- шаги пайплайна ----------

    def process_user_message(self, user_text: str) -> str:
        global FLAG
        user_text_lower = user_text.strip().lower()
        if user_text_lower == "stop":
            candidates = get_saved_candidates()
            urls = [val['url'] for val in candidates.values() if 'url' in val]
            if urls:
                top3 = urls[:3]
                links_text = "\n".join(f"{i + 1}. {url}" for i, url in enumerate(top3))
                FLAG = True
                return links_text
            else:
                return "К сожалению, подходящие товары не найдены."

        self.state.history.append(ChatMessage(role="user", content=user_text))

        if self.state.phase == "nlp":
            return self._step_nlp()
        else:
            return self._step_web()

    def _step_nlp(self) -> str:
        dialog = self._history_to_dialog_for_nlp()

        # ❗ Тут используем твой интерфейс NLP-агента.
        # Ниже — пример, ориентированный на формат:
        # {"status": "questions"|"ready"|"search", "questions": "...", "web_prompt": "...", ...}
        nlp_result = self.nlp_agent.process_dialog(dialog)

        self.state.last_nlp_result = nlp_result

        status = nlp_result.get("status", "questions")
        questions = nlp_result.get("questions") or nlp_result.get("answer") or ""

        # Добавляем ответ NLP в историю
        self.state.history.append(ChatMessage(role="assistant", content=questions))

        # Если всё ещё задаём вопросы — остаёмся в фазе nlp
        if status == "questions":
            return questions

        # Если NLP собрал всё, что нужно — переключаемся в web
        if status in ("ok", "search"):
            self.state.phase = "web"
            # Сразу делаем шаг web-агента
            web_answer = self._step_web()
            return questions + "\n\n" + web_answer

        # На всякий случай fallback
        return questions or "Я что-то не понял, давай попробуем переформулировать запрос."

    def _step_web(self) -> str:
        """
        Один вызов web-агента. В минимальной версии — просто один заход на маркетплейс.
        """
        history_text = self._history_to_text_for_web()

        # Пытаемся вытащить из NLP-результата промпт для поиска
        nlp_result = self.state.last_nlp_result or {}
        print(f"{nlp_result=}")
        # Подстрой под реальные поля, которые у тебя возвращает NLP:
        items = nlp_result.get("items", [])
        return self._step_web_for_items(items)


    def _step_web_for_items(self, items: list[dict]) -> str:
        """
        Обрабатывает ВСЕ items из первого агента:
        для каждой вещи формирует промпт и вызывает web-агента.
        """
        history_text = self._history_to_text_for_web()
        all_results: list[str] = []

        for idx, item in enumerate(items, start=1):
            # как получаем текстовый запрос для web-агента по каждой вещи:
            # 1) если первый агент уже положил его в поле web_prompt / prompt
            # 2) иначе собираем из структуру в строку
            web_prompt = (
                item.get("query")
                or item.get("prompt")
                or item.get("title")
            )

            if not web_prompt:
                # максимально тупой fallback – просто string(item)
                web_prompt = f"Найди вещь по описанию: {item}"

            print(f"\n[DEBUG] === Вещь #{idx} ===")
            print("[DEBUG] web_prompt:", web_prompt)
            print("[DEBUG] history_text:\n", history_text)
            print("-" * 60)

            web_result_text = run_agent(
                user_query=web_prompt,
                history_text=history_text,
            )

            # Кратко положим в history (чтобы не раздувать)
            short_for_history = textwrap.shorten(
                f"[#{idx}] {web_result_text}",
                width=400,
                placeholder="..."
            )
            self.state.history.append(
                ChatMessage(role="assistant", content=short_for_history)
            )

            # А пользователю вернём полный текст по каждой вещи
            block = (
                f"=== Вещь {idx} ===\n"
                f"Запрос: {web_prompt}\n\n"
                f"{web_result_text}\n"
            )
            all_results.append(block)
            candidates = get_saved_candidates()
            print(candidates)
            urls = [val['url'] for val in candidates.values()]
            agent, web_agent = get_agents(show_browser=True)
            share_url = web_agent.add_products_to_cart_and_get_share_link(urls, clear_before=True)

        # Итоговый текст: подряд результаты по всем вещам
        return "\n\n".join(all_results)



# --------- простой CLI, чтобы прогнать пайплайн локально ---------

def main():
    print("=== Минимальный NLP → WEB пайплайн ===")
    print("Напиши, что хочешь купить. 'exit' — выход.\n")

    adapter = MinimalAdapter()

    while True:
        user_text = input("Вы: ").strip()
        if not user_text:
            continue
        if user_text.lower() in ("exit", "quit", "q"):
            break

        answer = adapter.process_user_message(user_text)
        if FLAG:
            break
        print("\nАдаптер:", answer)
        print("\n" + "=" * 80 + "\n")
    print(answer)

if __name__ == "__main__":
    main()
