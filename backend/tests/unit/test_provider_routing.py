"""
Unit tests for the strict AI provider routing system.

These tests verify the core contract:
  - "ollama" never silently uses Gemini, and vice versa
  - "auto" only falls back to Gemini when Ollama is genuinely unavailable
  - Unknown provider values raise ValueError
  - Response tags match the resolved provider
"""

from unittest.mock import AsyncMock, patch

import pytest
from app.services.ai.ollama_client import MODEL_PRIORITY, select_best_model
from app.services.ai.provider_selector import (RESPONSE_TAGS, VALID_PROVIDERS,
                                               route_to_provider)


class TestValidProviders:
    def test_valid_providers_set(self):
        assert VALID_PROVIDERS == {"ollama", "gemini", "auto"}

    async def test_unknown_provider_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown provider"):
            await route_to_provider("test prompt", "claude")

    async def test_empty_provider_defaults_via_settings(self):
        """Empty string should resolve through settings.DEFAULT_AI_PROVIDER, not crash."""
        with patch(
            "app.services.ai.provider_selector.call_gemini",
            new=AsyncMock(return_value="mocked answer"),
        ), patch(
            "app.services.ai.provider_selector.is_ollama_running",
            new=AsyncMock(return_value=False),
        ):
            result = await route_to_provider("test prompt", "")
            assert result.provider_used in {"ollama", "gemini"}


class TestStrictOllamaRouting:
    async def test_ollama_strict_never_calls_gemini_on_success(self):
        with patch(
            "app.services.ai.provider_selector.call_ollama",
            new=AsyncMock(return_value=("local answer", "llama3.2:1b")),
        ) as mock_ollama, patch(
            "app.services.ai.provider_selector.call_gemini",
            new=AsyncMock(),
        ) as mock_gemini:
            result = await route_to_provider("test prompt", "ollama")

            assert result.provider_used == "ollama"
            assert result.tag == RESPONSE_TAGS["ollama"]
            assert result.text == "local answer"
            mock_ollama.assert_called_once()
            mock_gemini.assert_not_called()

    async def test_ollama_strict_raises_on_failure_never_falls_back(self):
        with patch(
            "app.services.ai.provider_selector.call_ollama",
            new=AsyncMock(side_effect=RuntimeError("Ollama not responding")),
        ), patch(
            "app.services.ai.provider_selector.call_gemini",
            new=AsyncMock(),
        ) as mock_gemini:
            with pytest.raises(RuntimeError, match="Ollama not responding"):
                await route_to_provider("test prompt", "ollama")

            mock_gemini.assert_not_called()


class TestStrictGeminiRouting:
    async def test_gemini_strict_never_calls_ollama_on_success(self):
        with patch(
            "app.services.ai.provider_selector.call_gemini",
            new=AsyncMock(return_value="cloud answer"),
        ) as mock_gemini, patch(
            "app.services.ai.provider_selector.call_ollama",
            new=AsyncMock(),
        ) as mock_ollama, patch(
            "app.services.ai.provider_selector.is_ollama_running",
            new=AsyncMock(),
        ) as mock_ping:
            result = await route_to_provider("test prompt", "gemini")

            assert result.provider_used == "gemini"
            assert result.tag == RESPONSE_TAGS["gemini"]
            assert result.text == "cloud answer"
            mock_gemini.assert_called_once()
            mock_ollama.assert_not_called()
            mock_ping.assert_not_called()

    async def test_gemini_strict_raises_on_failure_never_falls_back(self):
        with patch(
            "app.services.ai.provider_selector.call_gemini",
            new=AsyncMock(side_effect=RuntimeError("Gemini API failed")),
        ), patch(
            "app.services.ai.provider_selector.call_ollama",
            new=AsyncMock(),
        ) as mock_ollama:
            with pytest.raises(RuntimeError, match="Gemini API failed"):
                await route_to_provider("test prompt", "gemini")

            mock_ollama.assert_not_called()


class TestAutoRouting:
    async def test_auto_uses_ollama_when_running_with_models(self):
        with patch(
            "app.services.ai.provider_selector.is_ollama_running",
            new=AsyncMock(return_value=True),
        ), patch(
            "app.services.ai.provider_selector.list_models",
            new=AsyncMock(return_value=["llama3.2:1b", "mistral:7b"]),
        ), patch(
            "app.services.ai.provider_selector.call_ollama",
            new=AsyncMock(return_value=("local auto answer", "llama3.2:1b")),
        ) as mock_ollama, patch(
            "app.services.ai.provider_selector.call_gemini",
            new=AsyncMock(),
        ) as mock_gemini:
            result = await route_to_provider("test prompt", "auto")

            assert result.provider_used == "ollama"
            assert result.tag == RESPONSE_TAGS["auto-local"]
            mock_ollama.assert_called_once()
            mock_gemini.assert_not_called()

    async def test_auto_falls_back_to_gemini_when_ollama_not_running(self):
        with patch(
            "app.services.ai.provider_selector.is_ollama_running",
            new=AsyncMock(return_value=False),
        ), patch(
            "app.services.ai.provider_selector.call_gemini",
            new=AsyncMock(return_value="cloud auto answer"),
        ) as mock_gemini, patch(
            "app.services.ai.provider_selector.call_ollama",
            new=AsyncMock(),
        ) as mock_ollama:
            result = await route_to_provider("test prompt", "auto")

            assert result.provider_used == "gemini"
            assert result.tag == RESPONSE_TAGS["auto-cloud"]
            mock_gemini.assert_called_once()
            mock_ollama.assert_not_called()

    async def test_auto_falls_back_to_gemini_when_ollama_has_no_models(self):
        with patch(
            "app.services.ai.provider_selector.is_ollama_running",
            new=AsyncMock(return_value=True),
        ), patch(
            "app.services.ai.provider_selector.list_models",
            new=AsyncMock(return_value=[]),
        ), patch(
            "app.services.ai.provider_selector.call_gemini",
            new=AsyncMock(return_value="cloud auto answer"),
        ) as mock_gemini, patch(
            "app.services.ai.provider_selector.call_ollama",
            new=AsyncMock(),
        ) as mock_ollama:
            result = await route_to_provider("test prompt", "auto")

            assert result.provider_used == "gemini"
            assert result.tag == RESPONSE_TAGS["auto-cloud"]
            mock_ollama.assert_not_called()

    async def test_auto_propagates_gemini_failure_when_both_unavailable(self):
        with patch(
            "app.services.ai.provider_selector.is_ollama_running",
            new=AsyncMock(return_value=False),
        ), patch(
            "app.services.ai.provider_selector.call_gemini",
            new=AsyncMock(side_effect=RuntimeError("Gemini API failed")),
        ):
            with pytest.raises(RuntimeError, match="Gemini API failed"):
                await route_to_provider("test prompt", "auto")


class TestModelSelection:
    def test_select_best_model_prefers_llama3(self):
        models = ["mistral:7b", "llama3.2:1b", "phi3:mini"]
        assert select_best_model(models) == "llama3.2:1b"

    def test_select_best_model_falls_back_to_mistral(self):
        models = ["phi3:mini", "mistral:7b"]
        assert select_best_model(models) == "mistral:7b"

    def test_select_best_model_empty_list_returns_none(self):
        assert select_best_model([]) is None

    def test_select_best_model_unknown_model_returns_first(self):
        models = ["some-custom-model:latest"]
        assert select_best_model(models) == "some-custom-model:latest"

    def test_priority_order_is_deterministic(self):
        assert MODEL_PRIORITY.index("llama3") < MODEL_PRIORITY.index("mistral")
