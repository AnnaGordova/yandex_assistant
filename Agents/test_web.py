from Agents.web_agent.agent import run_agent, get_agents
from Agents.web_agent.web_tools import close_session, get_saved_candidates

MAX_HISTORY_CHARS = 2000


def interactive_dialog():
    """
    Простой CLI-диалог с web-агентом.
    Вводишь запросы, пока не напишешь 'stop'.
    История передаётся в агент как обычный текст,
    так что ошибка формата messages не возникает.
    """
    print("=== Web-агент для Яндекс.Маркета ===")
    print("Пиши запросы. Чтобы выйти, введи: stop\n")

    history_text = ""  # сюда будем складывать текстовую историю диалога
    user_input = """{
      "query": "женские треккинговые ботинки",
      "filters": {
        "sex": "female",
        "size": "37",
        "min_price": 4000,
        "max_price": null
      },
      "extra": "Подошва - Vibram или аналогичная по качеству (не сильно важно). Водонепроницаемые. В отзывах или покупках минимум 10 человек."
    }"""
    try:
        while True:

            if user_input.lower() in ("stop", "exit", "quit"):
                print("Останавливаем диалог.")
                break

            # Передаём всю накопленную историю как текст,
            # а не как внутренний список messages Qwen
            response_text = run_agent(
                user_query=user_input,
                history_text=history_text or None,
            )
            print("-" * 60)
            print("\n\n\nA:", response_text)
            print(get_saved_candidates())
            print("-" * 60)
            # Дописываем в историю последнюю реплику
            history_text += f"\nU: {user_input}\nA: {response_text}\n"
            if len(history_text) > MAX_HISTORY_CHARS:
                history_text = history_text[-MAX_HISTORY_CHARS:]

            user_input = input("U: ").strip()
            if not user_input:
                continue

    finally:
        candidates = get_saved_candidates()
        urls = [val['url'] for val in candidates.values()]
        agent, web_agent = get_agents(show_browser=True)
        share_url = web_agent.add_products_to_cart_and_get_share_link(urls, clear_before=True)
        print("Ссылка на корзину:", share_url)
        close_session()


if __name__ == "__main__":
    interactive_dialog()
