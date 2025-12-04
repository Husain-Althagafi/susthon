import os
import requests

API_KEY = os.getenv("GEMINI_API_KEY")
# Use a model that supports generateContent on v1beta; override via GEMINI_MODEL_NAME if needed.
MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")
API_URL = os.getenv(
    "GEMINI_API_URL",
    f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent",
)


class LLMClientError(Exception):
    pass


def generate_reply(prompt: str) -> str:
    if not API_KEY:
        raise LLMClientError("Missing GEMINI_API_KEY environment variable.")

    payload = {"contents": [{"role": "user", "parts": [{"text": prompt}]}]}

    try:
        response = requests.post(
            f"{API_URL}?key={API_KEY}",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        if not response.ok:
            try:
                detail = response.json().get("error", {}).get("message", "")
            except Exception:
                detail = response.text
            raise LLMClientError(f"LLM request failed ({response.status_code}): {detail}")

        data = response.json()
        candidates = data.get("candidates") or []
        if not candidates:
            raise LLMClientError("No candidates returned from Gemini.")
        text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
        return text.strip()
    except LLMClientError:
        raise
    except Exception as exc:
        raise LLMClientError(f"LLM request failed: {exc}") from exc
