"""Unit tests for RAG service - medical safety features."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.services.ai.rag_service import EMERGENCY_PATTERNS, MedicalRAGService


class TestEmergencyDetection:
    """Test emergency pattern detection - critical medical safety feature."""

    def setup_method(self):
        self.svc = MedicalRAGService()

    def test_detects_chest_pain(self):
        assert self.svc.detect_emergency("I have severe chest pain") is True

    def test_detects_breathing_difficulty(self):
        assert self.svc.detect_emergency("I can't breathe") is True
        assert self.svc.detect_emergency("Cannot breathe properly") is True
        assert self.svc.detect_emergency("shortness of breath suddenly") is True

    def test_detects_stroke_symptoms(self):
        assert self.svc.detect_emergency("I think I'm having a stroke") is True

    def test_detects_heart_attack(self):
        assert self.svc.detect_emergency("heart attack symptoms") is True

    def test_detects_severe_bleeding(self):
        assert self.svc.detect_emergency("severe bleeding that won't stop") is True

    def test_detects_unconscious(self):
        assert self.svc.detect_emergency("person is unconscious") is True
        assert self.svc.detect_emergency("loss of consciousness") is True

    def test_detects_seizure(self):
        assert self.svc.detect_emergency("having a seizure") is True

    def test_detects_overdose(self):
        assert self.svc.detect_emergency("possible overdose") is True

    def test_detects_anaphylaxis(self):
        assert self.svc.detect_emergency("anaphylaxis reaction") is True
        assert self.svc.detect_emergency("severe allergic reaction") is True

    def test_no_emergency_for_routine_query(self):
        assert self.svc.detect_emergency("what are symptoms of diabetes?") is False
        assert self.svc.detect_emergency("how to manage hypertension?") is False
        assert self.svc.detect_emergency("recommended dosage of metformin?") is False

    def test_case_insensitive_detection(self):
        assert self.svc.detect_emergency("CHEST PAIN severe") is True
        assert self.svc.detect_emergency("Heart Attack signs") is True

    def test_suicidal_ideation_detected(self):
        assert self.svc.detect_emergency("feeling suicidal") is True


class TestUnsafeContentDetection:
    def setup_method(self):
        self.svc = MedicalRAGService()

    def test_detects_unsafe_dosage_advice(self):
        assert (
            self.svc.detect_unsafe_content("take 5 times the dose for faster results")
            is True
        )

    def test_safe_medical_content(self):
        assert (
            self.svc.detect_unsafe_content(
                "consult your doctor before changing medications"
            )
            is False
        )
        assert (
            self.svc.detect_unsafe_content(
                "metformin is typically prescribed at 500mg twice daily"
            )
            is False
        )


class TestTextExtraction:
    def setup_method(self):
        self.svc = MedicalRAGService()

    def test_extract_txt(self):
        text = "This is medical content about diabetes."
        content = text.encode("utf-8")
        result = self.svc.extract_text(content, "txt")
        assert result == text

    def test_extract_markdown(self):
        md = "# Diabetes\n\nSome medical content here."
        content = md.encode("utf-8")
        result = self.svc.extract_text(content, "md")
        assert "Diabetes" in result

    def test_extract_csv(self):
        csv_content = "disease,symptoms\ndiabetes,polyuria\nhypertension,headache\n"
        content = csv_content.encode("utf-8")
        result = self.svc.extract_text(content, "csv")
        assert "diabetes" in result.lower()
        assert "hypertension" in result.lower()

    def test_unsupported_file_type_raises(self):
        with pytest.raises(ValueError, match="Unsupported file type"):
            self.svc.extract_text(b"content", "xyz")

    def test_extract_pdf_invalid_raises(self):
        with pytest.raises(Exception):
            self.svc.extract_text(b"not a pdf", "pdf")


class TestChunkingBehavior:
    def setup_method(self):
        self.svc = MedicalRAGService()

    def test_text_splitter_creates_chunks(self):
        long_text = "Medical information. " * 200
        chunks = self.svc.text_splitter.split_text(long_text)
        assert len(chunks) > 1

    def test_chunks_have_overlap(self):
        """Verify chunk overlap helps context continuity."""
        long_text = " ".join(
            [f"sentence{i} about medical topic{i}" for i in range(100)]
        )
        chunks = self.svc.text_splitter.split_text(long_text)
        if len(chunks) > 1:
            # Second chunk should contain some words from first chunk (overlap)
            first_chunk_words = set(chunks[0].split()[-20:])
            second_chunk_words = set(chunks[1].split()[:20])
            assert len(first_chunk_words & second_chunk_words) > 0
