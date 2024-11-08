from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Dict, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor

app = FastAPI()
executor = ThreadPoolExecutor()

jambonz_queue = asyncio.Queue()
other_ws_queue = asyncio.Queue()

@app.websocket("/dani_test")
async def dani_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            await websocket.send_json(data)
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print("Error:", e)

class Verb(BaseModel):
    verb: str
    text: str = None
    # Add other fields as needed based on Jambonz verb specifications

# WebSocket endpoint to handle data from Jambonz as if it were a webhook
@app.websocket("/jambonz-websocket")
async def jambonz_websocket(websocket: WebSocket):
    await websocket.accept(subprotocol="ws.jambonz.org")
    print("WebSocket connection established with Jambonz")
    try:
        while True:
            # Receive JSON data from Jambonz over WebSocket
            data = await websocket.receive_json()
            print("Received data:", data)

            # Example of processing the received data
            if data.get("type") == "session:new":
                # Example response for starting a call
                response = {
                    "type": "ack",
                    "msgid": data.get("msgid"),
                    "data": [
                        {
                            "input": ["speech"],
                            "verb": "gather",
                            "say": {
                                "text": "Ja qüasi hi som!",
                            }
                        }
                    ]
                }

                await websocket.send_json(response)

            elif data.get("type") == "call:status":
                # Process call status data as needed
                print("Received call status:", data)

            elif data.get("type") == "verb:hook":
                reason = data.get("data",{}).get("reason")
                if reason == "speechDetected":
                    speech = data.get("data").get("speech").get("transcripts")[0].get("alternatives")[0].get("transcript")

                    response = {
                        "type": "ack",
                        "msgid": data.get("msgid"),
                        "data": [
                            {
                                "verb": "gather",
                                "input": ["speech"],
                                "say": {
                                    "text": speech,
                                }
                            }
                        ]
                    }

                    await websocket.send_json(response)
            # For other events, you can handle as needed
            # Run a synchronous task in another thread if needed
            result = await asyncio.get_event_loop().run_in_executor(
                executor, sync_task_example, data
            )
            print("Sync task result:", result)

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print("Error:", e)

def sync_task_example(data):
    # Example synchronous code to process the data
    # Replace this with the actual sync task you need
    return f"Processed data: {data}"
