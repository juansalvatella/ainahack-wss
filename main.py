import asyncio

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Dict, Any

from concurrent.futures import ThreadPoolExecutor

from guide import get_step_by_path, path_map
from utils import gather_data
import salamandra

app = FastAPI()
executor = ThreadPoolExecutor()

jambonz_queue: asyncio.Queue[str] = asyncio.Queue()
other_ws_queue: asyncio.Queue[str] = asyncio.Queue()


@app.websocket("/extension")
async def extension_websocket(websocket: WebSocket):
    await websocket.accept()
    jambonz_task = asyncio.Task(act_on_jambonz_command(websocket))
    try:
        while True:
            data = await websocket.receive_json()
            await other_ws_queue.put(data)
            # await websocket.send_json(data)
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print("Error:", e)

async def act_on_jambonz_command(websocket: WebSocket):
    while True:
        jambonz_says: str = await jambonz_queue.get()
        await websocket.send_json(jambonz_says)

async def act_on_front_command(websocket: WebSocket):
    while True:
        message: str = await other_ws_queue.get()
        xpath = message.get("x_path", "")
        print(xpath)
        current_step = get_step_by_path(xpath)
        next_step = current_step + 1 % 7
        print(step)
        print(next_step)
        print(path_map[next_step])

        bot_message = f'Clica la opció de {path_map[next_step].get("text")}'

        await jambonz_queue.put({"x_path": path_map[next_step].get("x_path")})

        await websocket.send_json({
            "type": "command",
            "command": "redirect",
            "queueCommand": False,
            "data": [
                gather_data(bot_message)
            ]
        })

@app.websocket("/jambonz-websocket")
async def jambonz_websocket(websocket: WebSocket):
    await websocket.accept(subprotocol="ws.jambonz.org")
    print("WebSocket connection established with Jambonz")
    front_task = asyncio.Task(act_on_front_command(websocket))
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
                        gather_data("Hola! Em dic Olga i sóc l'assistent virtual del 012 quan ningú el pot atendre. En què el puc ajudar?"),
                    ]
                }

                await jambonz_queue.put({"x_path": path_map[1].get("x_path")})

                await websocket.send_json(response)

            elif data.get("type") == "call:status":
                # Process call status data as needed
                print("Received call status:", data)

            elif data.get("type") == "verb:hook":
                reason = data.get("data",{}).get("reason")
                print(data.get("data"))
                if reason == "speechDetected":
                    speech = data.get("data").get("speech").get("alternatives")[0].get("transcript")

                    await websocket.send_json({
                        "type": "ack",
                        "msgid": data.get("msgid"),
                        "data": [
                        ]
                    })

                    # await websocket.send_json({
                    #     "type": "command",
                    #     "command": "redirect",
                    #     "queueCommand": True,
                    #     "data": [
                    #         {
                    #             "verb": "gather",
                    #             "input": ["speech"],
                    #             "say": {
                    #                 "text": "",
                    #             },
                    #             "actionHook": actionHook
                    #         }
                    #     ]
                    # })

                    # response_salamandra = interact_salamandra(speech)
                    # print("---------------")
                    # print(response_salamandra)

                    # await websocket.send_json({
                    #     "type": "command",
                    #     "command": "redirect",
                    #     "queueCommand": True,
                    #     "data": [
                    #         {
                    #             "verb": "gather",
                    #             "input": ["speech"],
                    #             "say": {
                    #                 "text": response_salamandra,
                    #             },
                    #             "actionHook": actionHook
                    #         }
                    #     ]
                    # })

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
