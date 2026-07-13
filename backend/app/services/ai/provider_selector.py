"""
provider_selector.py
====================
Single source of truth for all AI provider routing in MedicalRAG.

Rules (STRICT — never violated):
  "ollama" → Ollama only. Failure = RuntimeError. No fallback.
  "gemini" → Gemini only. Failure = RuntimeError. No fallback.
  "auto"   → Try Ollama; if unavailable, use Gemini. Logged explicitly.

Response tags (always prefixed to answers):
  [OLLAMA]      — Ollama strict mode
  [GEMINI]      — Gemini strict mode
  [AUTO-LOCAL]  — auto resolved to Ollama
  [AUTO-CLOUD]  — auto resolved to Gemini
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.core.config import settings
from app.services.ai.gemini_client import call_gemini
from app.services.ai.ollama_client import (call_ollama, is_ollama_running,
                                           list_models, select_best_model)

logger = logging.getLogger(__name__)

RESPONSE_TAGS = {
    "ollama": "[OLLAMA]",
    "gemini": "[GEMINI]",
    "auto-local": "[AUTO-LOCAL]",
    "auto-cloud": "[AUTO-CLOUD]",
}

VALID_PROVIDERS = {"ollama", "gemini", "auto"}


@dataclass
class ProviderResult:
    tag: str  # prefix tag for the response
    provider_used: str  # "ollama" or "gemini"
    model_used: str
    endpoint: str
    text: str  # raw LLM output (no tag yet)


async def route_to_provider(
    prompt: str,
    provider: str,  # value from X-AI-Provider header
) -> ProviderResult:
    """
    Route prompt to the correct provider.
    Raises ValueError  for unknown provider strings.
    Raises RuntimeError if the chosen provider fails (caller returns [ERROR]).
    NEVER silently switches providers.
    """
    provider = (provider or settings.DEFAULT_AI_PROVIDER).strip().lower()

    if provider not in VALID_PROVIDERS:
        raise ValueError(
            f"Unknown provider '{provider}'. "
            f"Valid values: {sorted(VALID_PROVIDERS)}"
        )

    logger.info("[INFO] Provider selected: %s", provider)

    # ── OLLAMA (strict) ───────────────────────────────────────────────────────
    if provider == "ollama":
        logger.info("[INFO] Routing to: Ollama  (strict — no fallback)")
        logger.info("[INFO] Endpoint: %s/api/generate", settings.OLLAMA_BASE_URL)

        text, model = await call_ollama(prompt)  # raises on failure

        logger.info("[INFO] Final provider used: Ollama")
        logger.info("[INFO] Model name used: %s", model)

        return ProviderResult(
            tag=RESPONSE_TAGS["ollama"],
            provider_used="ollama",
            model_used=model,
            endpoint=f"{settings.OLLAMA_BASE_URL}/api/generate",
            text=text,
        )

    # ── GEMINI (strict) ───────────────────────────────────────────────────────
    if provider == "gemini":
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent"
        )
        logger.info("[INFO] Routing to: Gemini  (strict — no fallback)")
        logger.info("[INFO] Endpoint: %s", endpoint)

        text = await call_gemini(prompt)  # raises on failure

        logger.info("[INFO] Final provider used: Gemini")
        logger.info("[INFO] Model name used: %s", settings.GEMINI_MODEL)

        return ProviderResult(
            tag=RESPONSE_TAGS["gemini"],
            provider_used="gemini",
            model_used=settings.GEMINI_MODEL,
            endpoint=endpoint,
            text=text,
        )

    # ── AUTO ──────────────────────────────────────────────────────────────────
    if provider == "auto":
        logger.info("[INFO] Routing to: AUTO — pinging Ollama …")

        ollama_up = await is_ollama_running()

        if ollama_up:
            models = await list_models()
            best = select_best_model(models)

            if best:
                logger.info(
                    "[INFO] Ollama is available. Best model: %s  →  using AUTO-LOCAL",
                    best,
                )
                logger.info(
                    "[INFO] Endpoint: %s/api/generate", settings.OLLAMA_BASE_URL
                )

                text, model = await call_ollama(prompt, model=best)

                logger.info("[INFO] Final provider used: Ollama (AUTO-LOCAL)")
                logger.info("[INFO] Model name used: %s", model)

                return ProviderResult(
                    tag=RESPONSE_TAGS["auto-local"],
                    provider_used="ollama",
                    model_used=model,
                    endpoint=f"{settings.OLLAMA_BASE_URL}/api/generate",
                    text=text,
                )
            else:
                logger.warning(
                    "[WARN] Ollama is running but has NO installed models. "
                    "Switching to Gemini (AUTO-CLOUD)."
                )
        else:
            logger.warning(
                "[WARN] Ollama is not reachable at %s. "
                "Switching to Gemini (AUTO-CLOUD).",
                settings.OLLAMA_BASE_URL,
            )

        # ── AUTO → Gemini fallback (explicitly logged) ────────────────────────
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.GEMINI_MODEL}:generateContent"
        )
        logger.info("[INFO] Routing to: Gemini (AUTO-CLOUD)")
        logger.info("[INFO] Endpoint: %s", endpoint)

        text = await call_gemini(prompt)  # raises on failure

        logger.info("[INFO] Final provider used: Gemini (AUTO-CLOUD)")
        logger.info("[INFO] Model name used: %s", settings.GEMINI_MODEL)

        return ProviderResult(
            tag=RESPONSE_TAGS["auto-cloud"],
            provider_used="gemini",
            model_used=settings.GEMINI_MODEL,
            endpoint=endpoint,
            text=text,
        )
