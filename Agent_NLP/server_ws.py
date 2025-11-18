import asyncio
import json
import traceback
from websockets import serve
from Agent_NLP.agent_ws import Agent_nlp

agent = None


def extract_dialog(payload):
    """
    Поддерживаем два варианта входа:
    1) Клиент шлёт просто список сообщений: [...]
    2) Клиент шлёт {"dialog": [...]}.
    """
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("dialog"), list):
        return payload["dialog"]
    raise ValueError("Payload must be a list of messages or an object with 'dialog' field")


async def get_agent():
    """Извлечение экзамеляра класса агента"""
    global agent
    if agent is None:
        agent = Agent_nlp()
    return agent


async def handle_connection(websocket):
    """Соединение по сокетам"""
    print("New WebSocket connection")
    async for raw_message in websocket:
        try:
            data = json.loads(raw_message)
        except json.JSONDecodeError:
            err = {"status": "error", "message": "Invalid JSON"}
            await websocket.send(json.dumps(err, ensure_ascii=False))
            continue

        try:
            dialog = extract_dialog(data)
        except ValueError as e:
            err = {"status": "error", "message": str(e)}
            await websocket.send(json.dumps(err, ensure_ascii=False))
            continue

        try:
            ag = await get_agent()
            result = ag.process_dialog(dialog)
        except Exception as e:
            traceback.print_exc()
            result = {
                "status": "error",
                "message": f"Agent error: {e.__class__.__name__}: {e}"
            }

        print("<< RESP:", result)
        await websocket.send(json.dumps(result, ensure_ascii=False))


async def main():
    """Запуск сервера"""
    host = "127.0.0.1"
    port = 8766
    async with serve(handle_connection, host, port, ping_interval=None):
        print(f"NLP WebSocket server started on ws://{host}:{port}")
        await asyncio.Future()  # не даём процессу завершиться


if __name__ == "__main__":
    asyncio.run(main())
