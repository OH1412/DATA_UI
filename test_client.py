import asyncio, json
import websockets

async def main():
    async with websockets.connect("ws://127.0.0.1:8765/ws/telemetry") as ws:
        for _ in range(10):
            m=json.loads(await ws.recv())
            print("seq=",m["seq"],"head=",m["head"]["position"],"left_wrist=",m["body"]["joints"][20]["position"],"right_wrist=",m["body"]["joints"][21]["position"],"fps=",m["health"]["tracking_fps"])
asyncio.run(main())
