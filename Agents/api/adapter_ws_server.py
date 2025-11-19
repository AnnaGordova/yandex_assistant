# adapter_ws_server.py
import asyncio
import json
import traceback

import websockets  # pip install websockets
from websockets.exceptions import ConnectionClosedError

from adapter import Adapter

# Инициализируем адаптер в главном потоке
adapter = Adapter()


async def handle_connection(websocket):
    print("New WebSocket connection to Adapter (async)")
    try:
        async for raw_message in websocket:
            try:
                data = json.loads(raw_message)
            except json.JSONDecodeError:
                err = {
                    "message": "Некорректный JSON от клиента.",
                    "products": [],
                    "buttons": [],
                }
                await websocket.send(json.dumps(err, ensure_ascii=False))
                continue

            try:
                result = adapter.process_message_request(data)
            except Exception as e:
                traceback.print_exc()
                result = {
                    "message": f"Внутренняя ошибка адаптера: {e.__class__.__name__}: {e}",
                    "products": [],
                    "buttons": [],
                }

            print("<< RESP:", result)
            await websocket.send(json.dumps(result, ensure_ascii=False))

    except ConnectionClosedError as e:
        print(f"Connection closed: {e}")


async def main():
    host = "127.0.0.1"
    port = 8770

    # ping_interval=None, ping_timeout=None — отключаем keepalive,
    # чтобы длинные сессии web-агента не рвали соединение
    async with websockets.serve(
            handle_connection,
            host,
            port,
            ping_interval=None,
            ping_timeout=None,
            max_size=None,  # на всякий случай убираем лимит размера сообщений
    ):
        print(f"Async Adapter WebSocket server started on ws://{host}:{port}")
        # Вечное ожидание
        await asyncio.Future()


if __name__ == "__main__":
    import nest_asyncio

    nest_asyncio.apply()

    asyncio.run(main())
