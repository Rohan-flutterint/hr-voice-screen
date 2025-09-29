import os, json
from dotenv import load_dotenv
import httpx

# Model name to use with Ollama, e.g., 'llama3.2:3b-instruct' or 'llama3.1:8b-instruct'
def _get_model():
    load_dotenv()
    return os.getenv("LOCAL_LLM_MODEL", "llama3.2:3b-instruct")

def _chat(messages, temperature=0.2):
    # Call Ollama's /api/chat directly (no net)
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    url = f"{base}/api/chat"
    payload = {"model": _get_model(), "messages": messages, "stream": False, "options": {"temperature": temperature}}
    with httpx.Client(timeout=120.0) as client:
        r = client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
    return data["message"]["content"]

def chat_json(system: str, user: str):
    # Ask model to return JSON only; we'll attempt to parse
    messages = [
        {"role": "system", "content": system + "\\nReturn strictly JSON."},
        {"role": "user", "content": user}
    ]
    txt = _chat(messages)
    try:
        return json.loads(txt)
    except Exception:
        # try to coerce array
        if txt.strip().startswith("["):
            return json.loads(txt)
        return {"raw": txt}

def chat_text(system: str, user: str):
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user}
    ]
    return _chat(messages)