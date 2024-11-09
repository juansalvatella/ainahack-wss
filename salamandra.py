from transformers import AutoTokenizer
from sentence_transformers import SentenceTransformer

import requests
import os
import numpy as np

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