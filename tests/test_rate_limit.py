"""Tests for rate limiting middleware."""

import pytest
from time import sleep
from imagine.middleware.rate_limit import RateLimiter, RateLimitConfig


class TestRateLimiter:
    """Test cases for RateLimiter."""

    def test_initial_state_allows_requests(self):
        """New users should be allowed to make requests."""
        limiter = RateLimiter()
        result = limiter.check_message_rate(user_id=12345)
        assert result.allowed is True

    def test_initial_state_allows_generations(self):
        """New users should be allowed to generate."""
        limiter = RateLimiter()
        result = limiter.check_generation_rate(user_id=12345)
        assert result.allowed is True

    def test_message_rate_limit_per_minute(self):
        """Users exceeding per-minute message limit should be blocked."""
        config = RateLimitConfig(messages_per_minute=3, cooldown_seconds=5)
        limiter = RateLimiter(config=config)
        user_id = 12345

        # Send 3 messages (should all be allowed)
        for _ in range(3):
            result = limiter.check_message_rate(user_id)
            assert result.allowed is True
            limiter.record_message(user_id)

        # 4th message should be blocked
        result = limiter.check_message_rate(user_id)
        assert result.allowed is False
        assert result.retry_after_seconds is not None
        assert "Too many messages" in (result.message or "")

    def test_generation_rate_limit_per_minute(self):
        """Users exceeding per-minute generation limit should be blocked."""
        config = RateLimitConfig(generations_per_minute=2)
        limiter = RateLimiter(config=config)
        user_id = 12345

        # 2 generations should be allowed
        for _ in range(2):
            result = limiter.check_generation_rate(user_id)
            assert result.allowed is True
            limiter.record_generation(user_id)

        # 3rd generation should be blocked
        result = limiter.check_generation_rate(user_id)
        assert result.allowed is False
        assert "rate limit" in (result.message or "").lower()

    def test_record_generation_also_records_message(self):
        """Recording a generation should also count as a message."""
        config = RateLimitConfig(messages_per_minute=2)
        limiter = RateLimiter(config=config)
        user_id = 12345

        # Record 2 generations
        limiter.record_generation(user_id)
        limiter.record_generation(user_id)

        # Message rate should be exhausted
        result = limiter.check_message_rate(user_id)
        assert result.allowed is False

    def test_different_users_have_separate_limits(self):
        """Rate limits should be per-user."""
        config = RateLimitConfig(messages_per_minute=1)
        limiter = RateLimiter(config=config)

        # User 1 uses their limit
        limiter.record_message(user_id=1)
        result1 = limiter.check_message_rate(user_id=1)
        assert result1.allowed is False

        # User 2 should still be allowed
        result2 = limiter.check_message_rate(user_id=2)
        assert result2.allowed is True

    def test_get_user_stats(self):
        """Should return correct statistics for a user."""
        limiter = RateLimiter()
        user_id = 12345

        # Record some activity
        limiter.record_message(user_id)
        limiter.record_message(user_id)
        limiter.record_generation(user_id)

        stats = limiter.get_user_stats(user_id)
        
        # 2 messages + 1 generation (which also counts as message) = 3 messages
        assert stats["messages_last_minute"] == 3
        assert stats["generations_last_minute"] == 1

    def test_stats_for_unknown_user(self):
        """Should return zero stats for unknown users."""
        limiter = RateLimiter()
        stats = limiter.get_user_stats(user_id=99999)
        
        assert stats["messages_last_minute"] == 0
        assert stats["generations_last_day"] == 0


class TestRateLimitConfig:
    """Test cases for RateLimitConfig."""

    def test_default_config(self):
        """Default config should have reasonable defaults."""
        config = RateLimitConfig()
        
        assert config.messages_per_minute > 0
        assert config.messages_per_hour > 0
        assert config.generations_per_minute > 0
        assert config.generations_per_hour > 0
        assert config.generations_per_day > 0
        assert config.cooldown_seconds > 0

    def test_custom_config(self):
        """Custom config values should be applied."""
        config = RateLimitConfig(
            messages_per_minute=5,
            generations_per_day=10,
            cooldown_seconds=30
        )
        
        assert config.messages_per_minute == 5
        assert config.generations_per_day == 10
        assert config.cooldown_seconds == 30
