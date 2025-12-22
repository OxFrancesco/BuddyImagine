"""Tests for Pydantic models."""

import pytest
from pydantic import ValidationError
from imagine.models import GenerationRequest, UserSettings, CreditTransaction


class TestGenerationRequest:
    """Test cases for GenerationRequest model."""

    def test_valid_prompt(self):
        """Valid prompts should pass validation."""
        request = GenerationRequest(prompt="A beautiful sunset over the ocean")
        assert request.prompt == "A beautiful sunset over the ocean"

    def test_prompt_whitespace_stripped(self):
        """Prompts should have whitespace stripped."""
        request = GenerationRequest(prompt="  hello world  ")
        assert request.prompt == "hello world"

    def test_prompt_excessive_whitespace_normalized(self):
        """Excessive whitespace should be normalized."""
        request = GenerationRequest(prompt="hello    world")
        assert request.prompt == "hello world"

    def test_empty_prompt_rejected(self):
        """Empty prompts should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            GenerationRequest(prompt="")
        assert "min_length" in str(exc_info.value).lower() or "at least 1" in str(exc_info.value).lower()

    def test_whitespace_only_prompt_rejected(self):
        """Whitespace-only prompts should be rejected."""
        with pytest.raises(ValidationError):
            GenerationRequest(prompt="   ")

    def test_prompt_too_long_rejected(self):
        """Prompts over 2000 characters should be rejected."""
        long_prompt = "a" * 2001
        with pytest.raises(ValidationError):
            GenerationRequest(prompt=long_prompt)

    def test_model_id_optional(self):
        """Model ID should be optional."""
        request = GenerationRequest(prompt="test")
        assert request.model_id is None

    def test_valid_model_id(self):
        """Valid model IDs should pass validation."""
        request = GenerationRequest(prompt="test", model_id="fal-ai/flux/dev")
        assert request.model_id == "fal-ai/flux/dev"

    def test_invalid_model_id_rejected(self):
        """Model IDs with invalid characters should be rejected."""
        with pytest.raises(ValidationError):
            GenerationRequest(prompt="test", model_id="fal-ai/<script>")


class TestUserSettings:
    """Test cases for UserSettings model."""

    def test_default_values(self):
        """Default values should be applied."""
        settings = UserSettings()
        assert settings.telegram_quality == "uncompressed"
        assert settings.save_uncompressed_to_r2 is False
        assert settings.notify_low_credits is True
        assert settings.low_credit_threshold == 10.0

    def test_valid_telegram_quality_compressed(self):
        """Compressed quality should be valid."""
        settings = UserSettings(telegram_quality="compressed")
        assert settings.telegram_quality == "compressed"

    def test_invalid_telegram_quality_rejected(self):
        """Invalid quality values should be rejected."""
        with pytest.raises(ValidationError):
            UserSettings(telegram_quality="ultra-hd")

    def test_negative_threshold_rejected(self):
        """Negative thresholds should be rejected."""
        with pytest.raises(ValidationError):
            UserSettings(low_credit_threshold=-5)


class TestCreditTransaction:
    """Test cases for CreditTransaction model."""

    def test_valid_transaction(self):
        """Valid transactions should pass validation."""
        tx = CreditTransaction(
            amount=10.0,
            log_type="generation",
            description="Test generation"
        )
        assert tx.amount == 10.0
        assert tx.log_type == "generation"

    def test_zero_amount_rejected(self):
        """Zero amount should be rejected."""
        with pytest.raises(ValidationError):
            CreditTransaction(amount=0, log_type="generation", description="test")

    def test_negative_amount_rejected(self):
        """Negative amounts should be rejected."""
        with pytest.raises(ValidationError):
            CreditTransaction(amount=-5, log_type="generation", description="test")

    def test_invalid_log_type_rejected(self):
        """Invalid log types should be rejected."""
        with pytest.raises(ValidationError):
            CreditTransaction(amount=10, log_type="invalid_type", description="test")

    def test_valid_log_types(self):
        """All valid log types should be accepted."""
        valid_types = ["generation", "refund", "purchase", "admin", "subscription"]
        for log_type in valid_types:
            tx = CreditTransaction(amount=10, log_type=log_type, description="test")
            assert tx.log_type == log_type

    def test_empty_description_rejected(self):
        """Empty descriptions should be rejected."""
        with pytest.raises(ValidationError):
            CreditTransaction(amount=10, log_type="generation", description="")

    def test_description_too_long_rejected(self):
        """Descriptions over 500 characters should be rejected."""
        long_desc = "a" * 501
        with pytest.raises(ValidationError):
            CreditTransaction(amount=10, log_type="generation", description=long_desc)
