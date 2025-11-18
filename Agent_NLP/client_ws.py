import asyncio
import json
import websockets

WS_URL = "ws://127.0.0.1:8766"

async def main():
    """Клиент, который стучится к агенту на сервер"""
    dialog = []

    print("=== Тестовый клиент NLP-агента по WebSocket ===")
    print("Напишите, что хотите купить (например: 'футболка мужская')")

    first_msg = input("Вы: ").strip()
    if not first_msg:
        print("Пустой ввод, выходим.")
        return

    dialog.append({"role": "user", "content": first_msg})

    async with websockets.connect(WS_URL, ping_interval=None) as ws:
        while True:
            # отправляем на сервер всю историю диалога
            await ws.send(json.dumps(dialog, ensure_ascii=False))

            raw_resp = await ws.recv()

            try:
                resp = json.loads(raw_resp)
            except json.JSONDecodeError:
                print("Сервер вернул невалидный JSON:", raw_resp)
                break

            status = resp.get("status")

            if status == "error":
                print("Ошибка от сервера:", resp.get("message"))
                break

            if status == "ok":
                print("\n=== Статус OK. Финальные items для товарного агента ===")
                print(json.dumps(resp, ensure_ascii=False, indent=2))
                break

            if status == "questions":
                q_val = resp.get("questions")

                # поддержим и список, и строку
                if isinstance(q_val, list):
                    q_val = q_val[0] if q_val else None

                if not isinstance(q_val, str) or not q_val.strip():
                    print("status='questions', но вопрос пуст — выходим.")
                    break

                question = q_val.strip()

                print(f"\nАссистент: {question}")
                dialog.append({"role": "assistant", "content": question})

                answer = input("Вы: ").strip()
                dialog.append({"role": "user", "content": answer})

                # дальше пойдём в следующий цикл while -> новый запрос к серверу
                continue

            print("Неизвестный статус от сервера:", status)
            break


if __name__ == "__main__":
    asyncio.run(main())
