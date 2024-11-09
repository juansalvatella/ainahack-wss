import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Dict, Any

from concurrent.futures import ThreadPoolExecutor

from guide import get_step_by_path, path_map
from utils import gather_data, ACTION_HOOK

import salamandra
from time import sleep

app = FastAPI()
executor = ThreadPoolExecutor()

# Remove module-level queue definitions
# jambonz_queue: asyncio.Queue[Any] = asyncio.Queue()
# other_ws_queue: asyncio.Queue[Any] = asyncio.Queue()

@app.on_event("startup")
async def startup_event():
    # Create the queues within the application's event loop
    app.state.jambonz_queue = asyncio.Queue()
    app.state.other_ws_queue = asyncio.Queue()
    print("Queues created and background tasks started.")

@app.websocket("/extension")
async def extension_websocket(websocket: WebSocket):
    await websocket.accept()
    # Access the queues from app.state
    jambonz_queue = websocket.app.state.jambonz_queue
    other_ws_queue = websocket.app.state.other_ws_queue
    # Start the task to send messages from jambonz_queue to this websocket
    jambonz_task = asyncio.create_task(act_on_jambonz_command(websocket, jambonz_queue))
    try:
        while True:
            data = await websocket.receive_json()
            await other_ws_queue.put(data)
    except WebSocketDisconnect:
        print("Extension WebSocket disconnected")
    except Exception as e:
        print("Error in extension_websocket:", e)
    finally:
        jambonz_task.cancel()
        try:
            await jambonz_task
        except asyncio.CancelledError:
            pass

async def act_on_jambonz_command(websocket: WebSocket, jambonz_queue):
    while True:
        try:
            jambonz_says = await jambonz_queue.get()
            await websocket.send_json(jambonz_says)
        except asyncio.CancelledError:
            print("act_on_jambonz_command task cancelled")
            break  # Exit the loop when cancelled
        except Exception as e:
            print("Error in act_on_jambonz_command:", e)

async def act_on_front_command(websocket: WebSocket, other_ws_queue, jambonz_queue):
    while True:
        try:
            message = await other_ws_queue.get()
            print("message", message)
            xpath = message.get("x_path", [])
            print("XPath:", xpath)
            current_step = get_step_by_path(xpath)
            if not current_step:
               # If the xpath is not recognized, start again
               current_step = 0
               print("pasamos a current_step a 0")
            if current_step:
                next_step = (current_step + 1) % 7  # Fixed operator precedence
                print("Current step:", current_step)
                print("Next step:", next_step)
                print("Path map:", path_map[next_step])

                bot_message = f'Clica la opció de {path_map[next_step].get("text")}'

                print({"x_path": path_map[next_step].get("x_path")[0]})
                pause = path_map[next_step].get("pause", None)
                print("pause", pause)
                if pause:
                    print("waiting 2s")
                    await asyncio.sleep(2)

                await jambonz_queue.put({"x_path": path_map[next_step].get("x_path")[0]})

                await websocket.send_json({
                    "type": "command",
                    "command": "redirect",
                    "queueCommand": False,
                    "data": [
                        gather_data(bot_message)
                    ]
                })
        except asyncio.CancelledError:
            print("act_on_front_command task cancelled")
            break  # Exit the loop when cancelled
        except Exception as e:
            print("Error in act_on_front_command:", e)

@app.websocket("/jambonz-websocket")
async def jambonz_websocket(websocket: WebSocket):
    await websocket.accept(subprotocol="ws.jambonz.org")
    # Access the queues from app.state
    jambonz_queue = websocket.app.state.jambonz_queue
    other_ws_queue = websocket.app.state.other_ws_queue
    print("WebSocket connection established with Jambonz")
    # Start the task to process messages from other_ws_queue
    front_task = asyncio.create_task(act_on_front_command(websocket, other_ws_queue, jambonz_queue))
    try:
        while True:
            data = await websocket.receive_json()
            # print("Received data:", data)

            if data.get("type") == "session:new":
                response = {
                    "type": "ack",
                    "msgid": data.get("msgid"),
                    "data": [
                        gather_data("Hola! Em dic Olga i sóc l'assistent virtual del 012 quan ningú el pot atendre. En què el puc ajudar?"),
                    ]
                }

                print({"x_path": path_map[1].get("x_path")})
                await jambonz_queue.put({"x_path": path_map[1].get("x_path")})

                await websocket.send_json(response)

            elif data.get("type") == "call:status":
                # Process call status data as needed
                print("Received call status:", data)

            elif data.get("type") == "verb:hook":
                reason = data.get("data", {}).get("reason")
                print(data.get("data"))
                if reason == "speechDetected":
                    speech = data.get("data").get("speech").get("alternatives")[0].get("transcript")
                    print(speech)

                    await websocket.send_json({
                        "type": "ack",
                        "msgid": data.get("msgid"),
                        "data": []
                    })

                    # Additional processing as needed
                    response_salamandra = salamandra.interact_salamandra(speech)
                    print("---------------")
                    print(response_salamandra)

                    await websocket.send_json({
                        "type": "command",
                        "command": "redirect",
                        "queueCommand": True,
                        "data": [
                            {
                                "verb": "gather",
                                "input": ["speech"],
                                "say": {
                                    "text": response_salamandra.get("generated_text", ""),
                                },
                                "actionHook": ACTION_HOOK
                            }
                        ]
                    })

    except WebSocketDisconnect:
        print("Jambonz WebSocket disconnected")
    except Exception as e:
        print("Error in jambonz_websocket:", e)
    finally:
        front_task.cancel()
        try:
            await front_task
        except asyncio.CancelledError:
            pass

@app.websocket("/jambonz-status")
async def jambonz_status(websocket: WebSocket):
    await websocket.accept(subprotocol="ws.jambonz.org")
    try:
        while True:
            # Receive JSON data from Jambonz over WebSocket
            data = await websocket.receive_json()
            print("Received status:", data)
            await websocket.send_json({
                "type": "ack",
                "msgid": data.get("msgid")
            })
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print("Error:", e)
