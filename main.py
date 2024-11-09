import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import os

from concurrent.futures import ThreadPoolExecutor
import requests

from guide import get_step_by_path, path_map
from utils import gather_data, ACTION_HOOK, hangup

import salamandra
import phrases
from time import sleep

app = FastAPI()
executor = ThreadPoolExecutor()

stored_intent = "MULTA"

# Remove module-level queue definitions
# jambonz_queue: asyncio.Queue[Any] = asyncio.Queue()
# other_ws_queue: asyncio.Queue[Any] = asyncio.Queue()

@app.on_event("startup")
async def startup_event():
    # Create the queues within the application's event loop
    app.state.jambonz_queue = asyncio.Queue()
    app.state.other_ws_queue = asyncio.Queue()
    # app.state.selected_intent = DETECTED_INTENT
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

async def act_on_jambonz_command(websocket: WebSocket, jambonz_queue: asyncio.Queue):
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
    global stored_intent
    while True:
        try:
            message = await other_ws_queue.get()
            print("message", message)
            xpath = message.get("x_path", [])
            print("XPath:", xpath)
            current_step = get_step_by_path(stored_intent.upper(), xpath, path_map)
            if not current_step:
               # If the xpath is not recognized, start again
               current_step = 0
               print("pasamos a current_step a 0")

            if current_step or current_step == 0:
                next_step = (current_step + 1) % 7  # Fixed operator precedence
                print("Current step:", current_step)
                print("Next step:", next_step)
                print("Path map:", path_map[stored_intent.upper()][next_step])

                if xpath != "":
                    bot_message = f'Clica la opció de {path_map[stored_intent.upper()][next_step].get("text")}'
                else:
                    bot_message = "Doncs ja hi hem arribat. Si necessites res més no dubtis en trucar una altra vegada"
                print("bot_message", bot_message)

                print({"x_path": path_map[stored_intent.upper()][next_step].get("x_path")[0]})
                pause = path_map[stored_intent.upper()][next_step].get("pause", None)
                print("pause", pause)
                if pause:
                    print("waiting 2s")
                    await asyncio.sleep(1.5)

                await jambonz_queue.put({"x_path": path_map[stored_intent.upper()][next_step].get("x_path")[0]})

                await websocket.send_json({
                    "type": "command",
                    "command": "redirect",
                    "queueCommand": False,
                    "data": [
                        {
                            "verb": "say",
                            "text": bot_message,
                        }
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
    global stored_intent
    global path_map
    CONVERSATION_STATUS = "START"
    caller = None
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
            ANSWER = ""

            if data.get("type") == "session:new":
                caller = data.get("data").get("from")
                print("---------------------")
                print("SESSION NEW")
                response = {
                    "type": "ack",
                    "msgid": data.get("msgid"),
                    "data": [
                        gather_data(phrases.INTRO),
                    ]
                }
                await websocket.send_json(response)

            elif data.get("type") == "call:status":
                # Process call status data as needed
                print("Received call status:", data)

            elif data.get("type") == "verb:hook":
                reason = data.get("data", {}).get("reason")
                print(data.get("data"))
                await websocket.send_json({
                    "type": "ack",
                    "msgid": data.get("msgid"),
                    "data": []
                })
                if reason == "speechDetected":
                    speech = data.get("data").get("speech").get("alternatives")[0].get("transcript")
                    print(speech)

                    if CONVERSATION_STATUS == "START":
                        detected_intent = salamandra.classify_intent(speech, path_map.keys())
                        print("detected_intent", detected_intent.upper())
                        if detected_intent != "NONE":
                            stored_intent = detected_intent.upper()
                            CONVERSATION_STATUS = "USE_GOOGLE_CHROME"
                            ANSWER = phrases.USE_GOOGLE_CHROME
                        else:
                            ANSWER = phrases.NO_MATCH
                    elif CONVERSATION_STATUS == "USE_GOOGLE_CHROME":
                        confirmation = salamandra.detect_confirmation(speech)
                        if confirmation == "CONFIRMA":
                            CONVERSATION_STATUS = "START_FLOW"
                            ANSWER = phrases.START_FLOW
                        elif confirmation == "REBUTJA":
                            CONVERSATION_STATUS = "EXTENSION_REJECTED"
                            ANSWER = "En aquest cas, l'enviarem les instruccions per whats app i el transferirem a un dels nostres operadors. Moltes gràcies!"
                        else:
                            ANSWER = phrases.USE_GOOGLE_CHROME
                    elif CONVERSATION_STATUS == "START_FLOW":
                        pass

                    print("---------------")
                    print("CONVERSATION_STATUS",CONVERSATION_STATUS)
                    if CONVERSATION_STATUS == "START_FLOW":
                        CONVERSATION_STATUS = "IN_FLOW"
                        print({"x_path": path_map[stored_intent.upper()][1].get("x_path")})
                        await websocket.send_json({
                            "type": "command",
                            "command": "redirect",
                            "queueCommand": True,
                            "data": [
                                {
                                    "verb": "say",
                                    "text": ANSWER,
                                }
                            ]
                        })
                        await asyncio.sleep(3)
                        await jambonz_queue.put({"x_path": path_map[stored_intent.upper()][1].get("x_path")})
                    elif CONVERSATION_STATUS == "EXTENSION_REJECTED":
                        CONVERSATION_STATUS = "START"
                        await websocket.send_json({
                            "type": "command",
                            "command": "redirect",
                            "queueCommand": True,
                            "data": [
                                {
                                    "verb": "say",
                                    "text": ANSWER,
                                }
                            ]
                        })
                        send_whats_template(caller, stored_intent)
                        await websocket.send_json({
                            "type": "command",
                            "command": "redirect",
                            "queueCommand": True,
                            "data": [{
                                "verb": "dial",
                                "callerId": "012",
                                "actionHook": ACTION_HOOK,
                                "answerOnBridge": True,
                                "target": [
                                    {
                                    "type": "phone",
                                    "number": "+34618835151",
                                    "trunk": "Voxbone-j1kBDcms3ravVPBe5PjAwQ"
                                    },
                                ]
                            }]
                        })
                    else:
                        await websocket.send_json({
                            "type": "command",
                            "command": "redirect",
                            "queueCommand": True,
                            "data": [
                                {
                                    "verb": "gather",
                                    "input": ["speech"],
                                    "say": {
                                        "text": ANSWER,
                                    },
                                    "actionHook": ACTION_HOOK
                                }
                            ]
                        })
                    print("ANSWER",ANSWER)

                    # Additional processing as needed
                    # system_prompt = (
                    #     "Et dius Olga, respons al telèfon del 012 fora d'horari i ajudes a resoldre dubtes de la web de la generalitat"
                    # )
                    # response_salamandra = salamandra.interact_salamandra(speech, system_prompt=system_prompt)
                    # response_salamandra.get("generated_text", "")
                    

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

@app.post("/store_path_map")
async def store_path_map(request: Request):
    global path_map
    # Read the JSON data from the request
    raw_data = await request.json()
    
    # Convert string numeric keys to integers recursively
    def convert_keys_to_int(data):
        if isinstance(data, dict):
            return {int(k) if k.isdigit() else k: convert_keys_to_int(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [convert_keys_to_int(item) for item in data]
        else:
            return data

    path_map = {k: convert_keys_to_int(v) for k, v in raw_data.items()}
    print(path_map)
    return {"message": "Data stored successfully", "data_received": path_map}

@app.get("/instructions/{intent_id}", response_class=HTMLResponse)
async def get_instructions(intent_id: str):
    global path_map
    intent_key = intent_id.upper()
    message = "<html><body>\n"
    if intent_key in path_map:
        for _, step in path_map[intent_key].items():
            if step.get("text"):
                message += f'<p>Clica la opció de {step.get("text")}</p>\n'
    else:
        message += "<p>Intent ID not found.</p>\n"
    message += "</body></html>"
    return message

def send_whats_template(number: str, intent: str):
    payload: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": number,
        "type": "template",
        "template": {
            "language": {"policy": "deterministic", "code": "ca"},
            "name": "ainahack",
            "components": [{
                "type": "button",
                "sub_type": "url",
                "index": 0,
                "parameters": [
                    {
                        "type": "text",
                        # Business Developer-defined dynamic URL suffix
                        "text": intent
                    }
                ]
            }],
        },
    }
    url = "https://waba.360dialog.io/v1/messages"
    headers = {
        "D360-API-KEY": os.getenv("WHATSAPP_API", ""),
        "Content-Type": "application/json",
    }
    # 2 - Request and response
    response = requests.post(url, headers=headers, json=payload)
    print(response.content)