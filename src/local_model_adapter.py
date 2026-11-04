
import httpx
import os

OLLAMA_URL = os.environ.get("TRUSTSHIELD_OLLAMA_URL", "http://127.0.0.1:11434/api/generate")
MODEL_NAME = os.environ.get("TRUSTSHIELD_OLLAMA_MODEL", "llama3.2:1b")


def generate_local_response(prompt: str) -> str:
    if not prompt.strip():
        raise ValueError("Prompt cannot be empty")

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3,
            "num_predict": 160,
        },
    }

    with httpx.Client(timeout=60.0, trust_env=False) as client:
        result = client.post(
            OLLAMA_URL,
            json=payload
        )

        result.raise_for_status()
        data = result.json()

    if data.get("done") is not True:
        raise ValueError("Incomplete model response")

    answer = data.get("response")

    if not isinstance(answer, str):
        raise ValueError("Invalid model response")

    return answer
