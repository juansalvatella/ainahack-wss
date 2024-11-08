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
                                "text": "Això ja casi està",
                            },
                            "actionHook": "ws://120.86.175.34.bc.googleusercontent.com/jambonz-websocket"
                        }
                    ]
                }

                await websocket.send_json(response)

            elif data.get("type") == "call:status":
                # Process call status data as needed
                print("Received call status:", data)

            elif data.get("type") == "verb:hook":
                reason = data.get("data",{}).get("reason")
                print(data.get("data"))
                if reason == "speechDetected":
                    speech = data.get("data").get("speech").get("alternatives")[0].get("transcript")

                    response = {
                    "type": "ack",
                    "msgid": data.get("msgid"),
                    "data": [
                        {
                            "verb": "gather",
                            "input": ["speech"],
                            "say": {
                                "text": speech,
                            },
                            "actionHook": "ws://120.86.175.34.bc.googleusercontent.com/jambonz-websocket"
                        }
                    ]
                }

                    await websocket.send_json(response)

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print("Error:", e)

@app.websocket("/jambonz-status")
async def jambonz_status(websocket: WebSocket):
    await websocket.accept(subprotocol="ws.jambonz.org")

    try:
        while True:
            # Receive JSON data from Jambonz over WebSocket
            data = await websocket.receive_json()
            print("Received status:", data)
            await websocket.send_json({
                {
                    "type": "ack",
                    "msgid": data.get("msgid")
                }
            })

    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print("Error:", e)
