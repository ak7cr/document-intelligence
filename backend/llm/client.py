"""LLM dispatch layer — Ollama (default) or Gemini.

Configure via .env:
    LLM_PROVIDER=ollama          # or gemini
    OLLAMA_HOST=http://localhost:11434
    OLLAMA_MODEL=llama3.2
    GEMINI_API_KEY=<key>         # only needed for provider=gemini
    GEMINI_MODEL=gemini-1.5-flash
"""

import logging
import os

import requests

logger = logging.getLogger(__name__)

PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


def generate(prompt: str) -> str:
    """Generate a completion using the configured LLM provider."""
    if PROVIDER == "gemini":
        return _gemini(prompt)
    return _ollama(prompt)


def _ollama(prompt: str) -> str:
    try:
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Cannot connect to Ollama at {OLLAMA_HOST}. "
            "Start it with: ollama serve"
        )
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            raise RuntimeError(
                f"Model '{OLLAMA_MODEL}' not found in Ollama. "
                f"Pull it with: ollama pull {OLLAMA_MODEL}"
            )
        raise RuntimeError(f"Ollama error: {exc}") from exc


def _gemini(prompt: str) -> str:
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set in .env. "
            "Add it or switch LLM_PROVIDER=ollama."
        )
    try:
        import google.generativeai as genai
    except ImportError:
        raise RuntimeError(
            "google-generativeai is not installed. "
            "Run: pip install google-generativeai"
        )
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content(prompt)
    return response.text.strip()
