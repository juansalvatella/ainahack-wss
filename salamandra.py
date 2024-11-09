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
    'Respon sempre amb aquest format JSON: {"intent": "nom_de_la_intencio"}.'
]
embedder = SentenceTransformer('distiluse-base-multilingual-cased-v2')  # Multilingual model suitable for Catalan
document_embeddings = embedder.encode(documents, convert_to_tensor=False)

def classify_intent(text, intents):
    system_prompt = (
        'Les intencions possibles son' + f'{",".join(intents)}. Si no té sentit cap daquestes retorna NONE com a resultat'
    )
    answer = interact_salamandra(text, system_prompt)
    response = answer.get("generated_text")
    print("classify_intent", response)
    response_json = json.loads(response)
    return response_json.get("intent", "NONE")

def detect_confirmation(text):
    try:
        # Normalizamos el texto a minúsculas para facilitar la detección
        text = text.lower().strip()
        
        # Expresiones regulares para detectar confirmaciones
        confirm_patterns = r'\b(sí|si|confirmo|d\'acord|clar|evidentment|per descomptat|ok)\b'
        reject_patterns = r'\b(no|mai|nega|no pas|de cap manera)\b'

        if re.search(confirm_patterns, text):
            intent = "CONFIRMA"
        elif re.search(reject_patterns, text):
            intent = "REBUTJA"
        else:
            intent = "CONTINUA"
            
    except Exception as e:
        print(e)
        intent = "CONTINUA"

    # Devolver siempre el formato JSON esperado
    return intent


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