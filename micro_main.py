from web_agent.agent import run_agent
from web_agent.web_tools import close_session, get_saved_candidates

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
    user_input = """
    {
      "query": "телевизор для кухни, 32 дюйма, дешевый, с поддержкой Smart TV",
      "filters": {
        "sex": null,
        "size": null,
        "min_price": null,
        "max_price": 15000
      },
      "extra": "нужен недорогой телевизор 32 дюйма, с функцией Smart TV (чтобы можно было смотреть телевизор и интернет-контент), без дополнительных требований к дизайну, качеству звука и другим функциям"
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

            print("\n\n\nA:", response_text)
            print("-" * 60)
            print(get_saved_candidates())
            # Дописываем в историю последнюю реплику
            history_text += f"\nU: {user_input}\nA: {response_text}\n"
            if len(history_text) > MAX_HISTORY_CHARS:
                history_text = history_text[-MAX_HISTORY_CHARS:]

            user_input = input("U: ").strip()
            if not user_input:
                continue

    finally:
        close_session()


if __name__ == "__main__":
    interactive_dialog()
