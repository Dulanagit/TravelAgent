import asyncio
import websockets
import json

async def test():
    async with websockets.connect("ws://localhost:8001/ws/agent") as ws:
        await ws.send(json.dumps({"query": "I want to go to Colombo"}))
        
        while True:
            response = await ws.recv()
            data = json.loads(response)
            print("Received:", data["node"])
            if data["node"] == "hitl":
                print("Approving HITL...")
                await ws.send(json.dumps({"approved": True}))
            if data["node"] == "end":
                print("Finished!")
                break

asyncio.run(test())
