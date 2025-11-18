# adapter_ws_server.py
import asyncio
import json
import traceback
from websockets import serve
from adapter import Adapter

adapter = Adapter()

async def handle_connection(websocket):
    print("New WebSocket connection to Adapter")
    async for raw_message in websocket:
        try:
            data = json.loads(raw_message)
        except json.JSONDecodeError:
            err = {"status": "error", "message": "Invalid JSON"}
            await websocket.send(json.dumps(err, ensure_ascii=False))
            continue

        try:
            result = adapter.process_message_request(data)
        except Exception as e:
            traceback.print_exc()
            result = {
                "status": "error",
                "message": f"Adapter error: {e.__class__.__name__}: {e}",
            }

        print("<< RESP:", result)
        await websocket.send(json.dumps(result, ensure_ascii=False))


async def main():
    host = "127.0.0.1"
    port = 8770  # новый порт для адаптера
    async with serve(handle_connection, host, port, ping_interval=None):
        print(f"Adapter WebSocket server started on ws://{host}:{port}")
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
