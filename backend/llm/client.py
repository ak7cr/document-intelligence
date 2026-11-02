"""LLM dispatch layer — Ollama (default), Gemini, or Claude.

Configure via .env:
    LLM_PROVIDER=ollama          # ollama | gemini | claude
    OLLAMA_HOST=http://localhost:11434
    OLLAMA_MODEL=llama3.2
    GEMINI_API_KEY=<key>         # only needed for provider=gemini
    GEMINI_MODEL=gemini-1.5-flash
    ANTHROPIC_API_KEY=<key>      # only needed for provider=claude
    CLAUDE_MODEL=claude-sonnet-4-5
"""

import json
import logging
import os

import requests

logger = logging.getLogger(__name__)


def _provider() -> str:
    return os.getenv("LLM_PROVIDER", "ollama").strip().lower()


def _ollama_host() -> str:
    return os.getenv("OLLAMA_HOST", "http://localhost:11434")


def _ollama_model() -> str:
    return os.getenv("OLLAMA_MODEL", "llama3.2")


def _gemini_key() -> str:
    return os.getenv("GEMINI_API_KEY", "")


def _gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-1.5-flash")


def _claude_key() -> str:
    return os.getenv("ANTHROPIC_API_KEY", "")


def _claude_model() -> str:
    return os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")


def generate(prompt: str) -> str:
    """Generate a plain-text completion with the configured provider."""
    provider = _provider()
    if provider == "claude":
        return _claude(prompt)
    if provider == "gemini":
        return _gemini(prompt)
    return _ollama(prompt)


def generate_json(prompt: str, schema: dict | None = None, timeout: int = 180) -> str:
    """Generate a JSON completion.

    `schema` is enforced natively by Ollama (constrained decoding) and Gemini
    (response schema); Claude receives it as an explicit contract plus an
    assistant prefill so the reply is a JSON object.
    """
    provider = _provider()
    if provider == "claude":
        return _claude(prompt, schema=schema)
    if provider == "gemini":
        return _gemini(prompt, schema=schema)
    return _ollama(prompt, schema=schema, timeout=timeout)


def _ollama(prompt: str, schema: dict | None = None, timeout: int = 120) -> str:
    payload = {
        "model": _ollama_model(),
        "prompt": prompt,
        "stream": False,
    }
    if schema:
        payload["format"] = schema
    try:
        resp = requests.post(
            f"{_ollama_host()}/api/generate",
            json=payload,
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            f"Cannot connect to Ollama at {_ollama_host()}. "
            "Start it with: ollama serve"
        )
    except requests.exceptions.HTTPError as exc:
        if exc.response is not None and exc.response.status_code == 404:
            raise RuntimeError(
                f"Model '{_ollama_model()}' not found in Ollama. "
                f"Pull it with: ollama pull {_ollama_model()}"
            )
        raise RuntimeError(f"Ollama error: {exc}") from exc


def _gemini(prompt: str, schema: dict | None = None) -> str:
    api_key = _gemini_key()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set in .env. "
            "Add it or switch LLM_PROVIDER=ollama."
        )
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        raise RuntimeError(
            "google-genai is not installed. "
            "Run: pip install google-genai"
        )
    client = genai.Client(api_key=api_key)

    config = None
    if schema:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
        )
    try:
        response = client.models.generate_content(
            model=_gemini_model(),
            contents=prompt,
            config=config,
        )
    except Exception:
        if config is None:
            raise
        # Schema strictness varies by model; retry unconstrained rather than fail.
        logger.warning("Gemini structured-output call failed; retrying without schema")
        response = client.models.generate_content(
            model=_gemini_model(),
            contents=prompt,
        )
    return (response.text or "").strip()


def _claude_text(resp) -> str:
    if getattr(resp, "stop_reason", None) == "max_tokens":
        logger.warning("Claude reply hit max_tokens; output may be truncated")
    return "".join(
        block.text for block in resp.content
        if getattr(block, "type", "") == "text"
    ).strip()


def _strict_schema(schema: dict) -> dict:
    """Claude's json_schema output requires additionalProperties: false on objects."""
    import copy

    strict = copy.deepcopy(schema)

    def walk(node) -> None:
        if isinstance(node, dict):
            if node.get("type") == "object" and "additionalProperties" not in node:
                node["additionalProperties"] = False
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(strict)
    return strict


def _claude(prompt: str, schema: dict | None = None) -> str:
    api_key = _claude_key()
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY is not set in .env. "
            "Add it or switch LLM_PROVIDER=ollama."
        )
    try:
        import anthropic
    except ImportError:
        raise RuntimeError(
            "anthropic is not installed. Run: pip install anthropic"
        )

    client = anthropic.Anthropic(api_key=api_key)
    common = {
        "model": _claude_model(),
        "max_tokens": int(os.getenv("CLAUDE_MAX_TOKENS", "8192")),
        "timeout": 180.0,
    }

    try:
        if not schema:
            resp = client.messages.create(
                **common,
                messages=[{"role": "user", "content": prompt}],
            )
            return _claude_text(resp)

        # Preferred: native structured output (schema-conformant JSON).
        try:
            resp = client.messages.create(
                **common,
                messages=[{"role": "user", "content": prompt}],
                output_config={
                    "format": {"type": "json_schema", "schema": _strict_schema(schema)}
                },
            )
            return _claude_text(resp)
        except anthropic.BadRequestError as exc:
            logger.warning(
                "Claude rejected json_schema output (%s); retrying with prefill", exc
            )

        # Fallback: schema in prompt + assistant prefill forces a JSON object.
        resp = client.messages.create(
            **common,
            system=(
                "You are a precise document-analysis engine. Reply with one valid "
                "JSON object only — no markdown fences, no commentary."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"{prompt}\n\nThe JSON object MUST conform to this JSON Schema:\n"
                        f"{json.dumps(schema)}"
                    ),
                },
                {"role": "assistant", "content": "{"},
            ],
        )
        return "{" + _claude_text(resp)
    except anthropic.APIError as exc:
        raise RuntimeError(f"Claude error: {exc}") from exc


