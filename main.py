import asyncio
import requests
import os
import numpy as np

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Dict, Any
from transformers import AutoTokenizer
from sentence_transformers import SentenceTransformer
from concurrent.futures import ThreadPoolExecutor

from guide import get_step_by_path, path_map

app = FastAPI()
executor = ThreadPoolExecutor()

jambonz_queue: asyncio.Queue[str] = asyncio.Queue()
other_ws_queue: asyncio.Queue[str] = asyncio.Queue()

memory = []

actionHook = "ws://120.86.175.34.bc.googleusercontent.com/jambonz-websocket"

BASE_URL = "https://j292uzvvh7z6h2r4.us-east-1.aws.endpoints.huggingface.cloud"
model_name = "BSC-LT/salamandra-7b-instruct-aina-hack"
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

# 1. Knowledge Base
documents = [
    "A la web de la generalitat pots pagar les multes de tràsit",
    "Es pot pagar amb tarjeta de crèdit o domiciliació bancaria",
]
embedder = SentenceTransformer('distiluse-base-multilingual-cased-v2')  # Multilingual model suitable for Catalan
document_embeddings = embedder.encode(documents, convert_to_tensor=False)

def interact_salamandra(text):
    # Your existing imports and variables
    headers = {
        "Accept": "application/json",
        "Authorization": f'Bearer {os.getenv("HF_TOKEN", "")}',
        "Content-Type": "application/json"
    }

    query_embedding = embedder.encode(text, convert_to_tensor=False)

    # 4. Compute Similarities
    cosine_scores = np.dot(document_embeddings, query_embedding)

    # 5. Retrieve Top-K Relevant Documents
    top_k = 1
    top_k_indices = np.argsort(cosine_scores)[::-1][:top_k]
    retrieved_docs = [documents[i] for i in top_k_indices]

    # 6. Integrate Retrieved Information
    retrieved_text = "\n".join(retrieved_docs)
    user_message_with_context = f"{text}\n\nInformació rellevant:\n{retrieved_text}"

    # 7. Prepare the Messages
    system_prompt = (
        "Ajudes a gent gran a resoldre dubtes de la pàgina web de la generalitat"
        "Ho has d'explicar tot amb molt detall, molt a poc a poc i de forma molt amable."
    )
    message = [{"role": "system", "content": system_prompt}]
    message += [{"role": "user", "content": user_message_with_context}]

    # 8. Generate the Prompt
    prompt = tokenizer.apply_chat_template(
        message,
        tokenize=False,
        add_generation_prompt=True,
    )

    # 9. Make the API Call
    payload = {
        "inputs": prompt,
        "parameters": {}
    }
    api_url = BASE_URL + "/generate"
    response = requests.post(api_url, headers=headers, json=payload)
    return response.json().get("generated_text", "")

@app.websocket("/extension")
async def extension_websocket(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            text = data.get("text", "")
            await other_ws_queue.put(text)
            # await websocket.send_json(data)
    except WebSocketDisconnect:
        print("WebSocket disconnected")
    except Exception as e:
        print("Error:", e)

class Verb(BaseModel):
    verb: str
    text: str = None
    # Add other fields as needed based on Jambonz verb specifications

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

        await jambonz_queue.put({"x_path": next_step})

        await websocket.send_json({
            "type": "command",
            "command": "redirect",
            "queueCommand": False,
            "data": [
                {
                    "verb": "gather",
                    "input": ["speech"],
                    "say": {
                        "text": bot_message,
                    },
                    "actionHook": actionHook
                }
            ]
        })
        # await websocket.send_json({
        #     "type": "command",
        #     "command": "redirect",
        #     "queueCommand": False,
        #     "data": [
        #         {
        #             "verb": "say",
        #             "text": front_says,
        #         }
        #     ]
        # })

# WebSocket endpoint to handle data from Jambonz as if it were a webhook
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
                        {
                            "input": ["speech"],
                            "verb": "gather",
                            "say": {
                                "text": "Hola! Em dic Olga i sóc l'assistent virtual del 012 quan ningú el pot atendre. En què el puc ajudar?",
                            },
                            "actionHook": actionHook
                        }
                    ]
                }

                await jambonz_queue.put({"x_path": 1})

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
