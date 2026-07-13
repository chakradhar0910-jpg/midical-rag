"""
Ollama local LLM client for MedicalRAG.
Strict: raises RuntimeError on failure — caller must NOT silently fall back.
"""

import asyncio
import logging
from typing import Optional

import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

OLLAMA_BASE = settings.OLLAMA_BASE_URL
OLLAMA_GENERATE = f"{OLLAMA_BASE}/api/generate"
OLLAMA_TAGS = f"{OLLAMA_BASE}/api/tags"
OLLAMA_TIMEOUT = settings.OLLAMA_TIMEOUT_SECONDS

# Priority order: highest-capability models first
MODEL_PRIORITY = [
    "llama3",
    "llama3.2",
    "llama3.1",
    "llama3:8b",
    "llama3:70b",
    "llama2",
    "mistral",
    "mixtral",
    "gemma2",
    "gemma",
    "phi3",
    "phi",
    "qwen",
    "deepseek",
    "codellama",
    "vicuna",
    "orca",
]


async def is_ollama_running() -> bool:
    """Return True if Ollama is reachable."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(OLLAMA_TAGS)
            return r.status_code == 200
    except Exception:
        return False


async def list_models() -> list[str]:
    """Return names of all locally installed Ollama models."""
    # Try REST API first
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(OLLAMA_TAGS)
            if r.status_code == 200:
                return [m["name"] for m in r.json().get("models", [])]
    except Exception:
        pass

    # Fallback: subprocess `ollama list`
    try:
        proc = await asyncio.create_subprocess_exec(
            "ollama",
            "list",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        lines = stdout.decode().strip().splitlines()
        models = []
        for line in lines[1:]:  # skip header
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models
    except Exception:
        return []


def select_best_model(available: list[str]) -> Optional[str]:
    """Pick highest-priority installed model. Returns None if list is empty."""
    if not available:
        return None
    low = {m.lower(): m for m in available}
    for priority in MODEL_PRIORITY:
        for name_lower, name_orig in low.items():
            if name_lower.startswith(priority):
                return name_orig
    return available[0]


async def call_ollama(prompt: str, model: Optional[str] = None) -> tuple[str, str]:
    """
    Send prompt to Ollama; return (response_text, model_used).
    Raises RuntimeError on any failure.
    """
    if model is None:
        model = settings.OLLAMA_DEFAULT_MODEL or None

    if model is None:
        models = await list_models()
        model = select_best_model(models)
        if not model:
            raise RuntimeError(
                "No Ollama models installed. Run: ollama pull llama3.2:1b"
            )

    logger.info("[INFO] Model name used: %s", model)
    logger.info("[INFO] Endpoint: %s", OLLAMA_GENERATE)

    payload = {"model": model, "prompt": prompt, "stream": False}

    try:
        async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
            response = await client.post(OLLAMA_GENERATE, json=payload)

        if response.status_code != 200:
            raise RuntimeError(
                f"Ollama HTTP {response.status_code}: {response.text[:300]}"
            )

        text = response.json().get("response", "").strip()
        if not text:
            raise RuntimeError("Ollama returned an empty response")

        return text, model

    except httpx.TimeoutException as exc:
        raise RuntimeError(
            f"Ollama timed out after {OLLAMA_TIMEOUT}s. "
            "Try a smaller model or increase OLLAMA_TIMEOUT_SECONDS."
        ) from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"Ollama network error: {exc}") from exc
