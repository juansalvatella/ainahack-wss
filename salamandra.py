from transformers import AutoTokenizer
from sentence_transformers import SentenceTransformer

import requests
import os
import numpy as np
import json

BASE_URL = "https://j292uzvvh7z6h2r4.us-east-1.aws.endpoints.huggingface.cloud"
model_name = "BSC-LT/salamandra-7b-instruct-aina-hack"
tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

# 1. Knowledge Base
documents = [
    "Pots pagar les multes de trànsit a la web de la Generalitat.",
    "L'Administració ha de notificar-te la denúncia en un termini màxim de 3 mesos per a infraccions lleus i de 6 mesos per a infraccions greus o molt greus.",
    "Tens 20 dies naturals per pagar amb una reducció del 50% després de rebre la notificació.",
    "Si no reps la notificació, pots consultar les sancions al DOGC, BOE o butlletins oficials provincials.",
    "Per consultar sancions al DOGC, cerca pel número del DNI.",
    "Per consultar sancions al BOE, utilitza el sistema Cl@ve per accedir al Taulell Edictal Únic.",
    "Pots consultar expedients de sancions en línia amb identificació digital (idCAT, idCAT Mòbil, FNMT, etc.).",
    "Si tens certificat digital, pots subscriure't a notificacions electròniques per rebre avisos de sancions.",
    "La multa sempre arriba al titular del vehicle. Si no conduïes, pots identificar el conductor.",
    "Si estàs en desacord amb la sanció, pots presentar al·legacions en un termini de 20 dies naturals després de la notificació.",
    "Si has fet el pagament i es resolen a favor teu les al·legacions, pots demanar la devolució dels ingressos indeguts.",
    "Per obtenir més detalls, visita la pàgina oficial de la Generalitat."
]
embedder = SentenceTransformer('distiluse-base-multilingual-cased-v2')  # Multilingual model suitable for Catalan
document_embeddings = embedder.encode(documents, convert_to_tensor=False)

def classify_intent(text, intents):
    system_prompt = (
        'Respon sempre amb aquest format JSON: {"intent": "nom_de_la_intencio"}. Les intencions possibles son' + f'{",".join(intents)}. Si no té sentit cap daquestes retorna NONE com a resultat'
    )
    answer = interact_salamandra(text, system_prompt)
    response = answer.get("generated_text")
    response_json = json.loads(response)
    return response_json.get("intent", "NONE")

def detect_confirmation(text):
    system_prompt = (
        'Respon sempre amb aquest format JSON: {"intent": "nom_de_la_intencio"}. Les intencions possibles son "CONFIRMA" si confirma o diu que si, "REBUTJA" si diu que no i "CONTINUA" si no és cap de les dos'
    )
    answer = interact_salamandra(text, system_prompt)
    response = answer.get("generated_text")
    response_json = json.loads(response)
    return response_json.get("intent", "CONTINUA")


def interact_salamandra(text, system_prompt):
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
    return response.json()