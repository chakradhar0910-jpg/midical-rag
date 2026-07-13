"""AI provider health check and info endpoints."""

import logging

from app.core.config import settings
from app.schemas.schemas import AIProviderHealth
from app.services.ai.ollama_client import is_ollama_running, list_models
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai", tags=["AI Provider"])


@router.get(
    "/health",
    response_model=AIProviderHealth,
    summary="Check availability of all AI providers",
    description=(
        "Returns real-time status of Ollama (local) and Gemini (cloud). "
        "Lists all installed Ollama models. Checks if Gemini API key is configured."
    ),
)
async def ai_health() -> AIProviderHealth:
    """
    GET /api/v1/ai/health

    Returns:
      - ollama_running: bool
      - available_models: list of installed Ollama model names
      - gemini_available: bool (True if GEMINI_API_KEY is set)
      - default_provider: configured DEFAULT_AI_PROVIDER setting
    """
    logger.info("[HEALTH] Checking AI provider health …")

    ollama_up = await is_ollama_running()
    models: list[str] = []
    if ollama_up:
        models = await list_models()

    gemini_ok = bool(settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "")

    logger.info(
        "[HEALTH] ollama_running=%s  models=%s  gemini_available=%s  default=%s",
        ollama_up,
        models,
        gemini_ok,
        settings.DEFAULT_AI_PROVIDER,
    )

    return AIProviderHealth(
        ollama_running=ollama_up,
        available_models=models,
        gemini_available=gemini_ok,
        default_provider=settings.DEFAULT_AI_PROVIDER,
    )


@router.get(
    "/providers",
    summary="List supported provider values",
)
async def list_providers():
    """
    GET /api/v1/ai/providers

    Returns supported X-AI-Provider header values and their descriptions.
    """
    return {
        "supported_providers": [
            {
                "value": "ollama",
                "label": "Ollama (local)",
                "description": "Uses local Ollama inference. Fails with [ERROR] if Ollama is not running. Never falls back to Gemini.",
                "tag": "[OLLAMA]",
                "timeout_seconds": settings.OLLAMA_TIMEOUT_SECONDS,
            },
            {
                "value": "gemini",
                "label": "Gemini (cloud)",
                "description": "Uses Google Gemini API. Fails with [ERROR] if key is missing or call fails. Never falls back to Ollama.",
                "tag": "[GEMINI]",
                "timeout_seconds": settings.GEMINI_TIMEOUT_SECONDS,
            },
            {
                "value": "auto",
                "label": "Auto (recommended)",
                "description": "Tries Ollama first. Falls back to Gemini only if Ollama is unavailable or has no models. Both steps are logged explicitly.",
                "tag_local": "[AUTO-LOCAL]",
                "tag_cloud": "[AUTO-CLOUD]",
            },
        ],
        "default_provider": settings.DEFAULT_AI_PROVIDER,
        "header_name": "X-AI-Provider",
    }
