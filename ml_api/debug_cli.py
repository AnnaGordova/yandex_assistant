import asyncio
import json
import uuid

import websockets  # pip install websockets


WS_URI = "ws://127.0.0.1:8770"


async def dialog_client():
    # Один токен на всю сессию (как будто один пользователь)
    token = "debug-" + uuid.uuid4().hex[:8]
    email = "test@example.com"

    # Параметры можно захардкодить для дебага
    params = {
        "address": "Москва, Россия",
        "budget": "10000",
        "wishes": "комфортно и стильно",
    }

    chat_history = []  # список {text, isUser}
    last_buttons = []  # список кнопок из последнего ответа

    print(f"Подключаюсь к {WS_URI} с token={token} ...")
    async with websockets.connect(WS_URI, ping_interval=None) as ws:
        print("Готово! Пиши сообщение. 'exit' — выход.\n")

        while True:
            # Показать последние кнопки, если есть
            if last_buttons:
                print("\nДоступные кнопки:")
                for i, btn in enumerate(last_buttons, start=1):
                    text = btn.get("text", "")
                    value = btn.get("value", "")
                    print(f"  [{i}] {text}  ({value})")
                print("Можешь ввести номер кнопки, чтобы 'нажать' её.\n")

            user_input = input("Вы: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("exit", "quit", "q"):
                break

            # Если пользователь ввёл число и есть кнопки — считаем это нажатием кнопки
            message_to_send = user_input
            if user_input.isdigit() and last_buttons:
                idx = int(user_input)
                if 1 <= idx <= len(last_buttons):
                    btn = last_buttons[idx - 1]
                    message_to_send = btn.get("value", "")
                    print(f"(нажата кнопка [{idx}] → message={message_to_send!r})")

            # Добавляем ход пользователя в историю
            chat_history.append({"text": message_to_send, "isUser": True})

            payload = {
                "email": email,
                "message": message_to_send,
                "token": token,
                "params": params,
                "chatHistory": chat_history,
            }

            # Отправляем запрос
            await ws.send(json.dumps(payload, ensure_ascii=False))
            raw_resp = await ws.recv()

            try:
                resp = json.loads(raw_resp)
            except json.JSONDecodeError:
                print("\n‼️ Не удалось распарсить ответ как JSON:")
                print(raw_resp)
                continue

            # Разбираем ответ адаптера: MessageAnswer
            message = resp.get("message") or ""
            products = resp.get("products") or []
            buttons = resp.get("buttons") or []

            # Логика: текст ассистента добавляем в историю
            if message:
                chat_history.append({"text": message, "isUser": False})

            # Печатаем ответ
            print("\nАссистент:")
            print(message or "(пустое сообщение)")

            if products:
                print("\nТовары:")
                for i, p in enumerate(products, start=1):
                    name = p.get("name", "")
                    price = p.get("price", 0)
                    link = p.get("link", "")
                    rating = p.get("rating", 0)
                    reviews = p.get("ammountOfReviews", 0)
                    size = p.get("size") or ""
                    print(f"  #{i}: {name}")
                    print(f"      Цена: {price} ₽, рейтинг: {rating} ({reviews} отзывов), размер: {size}")
                    print(f"      Ссылка: {link}")
                print()

            # Сохраняем кнопки для следующего шага
            last_buttons = buttons

            print("-" * 80)


if __name__ == "__main__":
    asyncio.run(dialog_client())
