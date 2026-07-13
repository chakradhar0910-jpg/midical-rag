"""
Gemini cloud LLM client for MedicalRAG.
Strict: raises RuntimeError on failure — caller must NOT silently fall back.
"""

import logging

import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent?key={key}"
)
GEMINI_TIMEOUT = settings.GEMINI_TIMEOUT_SECONDS


async def call_gemini(prompt: str) -> str:
    """
    Send prompt to Gemini API; return response text.
    Raises RuntimeError on any failure.
    """
    if not settings.GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not configured. " "Set it in backend/.env and restart."
        )

    model = settings.GEMINI_MODEL
    url = GEMINI_ENDPOINT.format(model=model, key=settings.GEMINI_API_KEY)

    safe_url = url.split("?")[0]  # hide API key in logs
    logger.info("[INFO] Model name used: %s", model)
    logger.info("[INFO] Endpoint: %s", safe_url)

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 1500,
        },
    }

    try:
        async with httpx.AsyncClient(timeout=GEMINI_TIMEOUT) as client:
            response = await client.post(url, json=payload)

        if response.status_code != 200:
            raise RuntimeError(
                f"Gemini HTTP {response.status_code}: {response.text[:300]}"
            )

        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
            raise RuntimeError("Gemini returned no candidates")

        text = (
            candidates[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "")
            .strip()
        )
        if not text:
            raise RuntimeError("Gemini returned an empty text response")

        return text

    except httpx.TimeoutException as exc:
        raise RuntimeError(f"Gemini timed out after {GEMINI_TIMEOUT}s") from exc
    except httpx.RequestError as exc:
        raise RuntimeError(f"Gemini network error: {exc}") from exc
