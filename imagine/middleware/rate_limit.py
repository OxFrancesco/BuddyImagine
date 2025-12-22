"""Rate limiting middleware for Telegram bot."""

from collections import defaultdict
from dataclasses import dataclass, field
from time import time
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    # General message rate limits
    messages_per_minute: int = 20
    messages_per_hour: int = 100
    
    # Generation-specific limits
    generations_per_minute: int = 5
    generations_per_hour: int = 30
    generations_per_day: int = 100
    
    # Cooldown after hitting limit (seconds)
    cooldown_seconds: int = 60


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    retry_after_seconds: Optional[int] = None
    message: Optional[str] = None


class RateLimiter:
    """In-memory rate limiter for bot requests.
    
    Note: For distributed deployments (webhooks), consider using
    Convex or Redis for shared state across instances.
    """
    
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        # user_id -> list of timestamps
        self._message_timestamps: dict[int, list[float]] = defaultdict(list)
        self._generation_timestamps: dict[int, list[float]] = defaultdict(list)
        # Track users in cooldown
        self._cooldowns: dict[int, float] = {}
    
    def _cleanup_old_entries(self, timestamps: list[float], max_age_seconds: float) -> list[float]:
        """Remove entries older than max_age_seconds."""
        now = time()
        cutoff = now - max_age_seconds
        return [ts for ts in timestamps if ts > cutoff]
    
    def check_message_rate(self, user_id: int) -> RateLimitResult:
        """Check if user can send a message."""
        now = time()
        
        # Check if user is in cooldown
        if user_id in self._cooldowns:
            cooldown_end = self._cooldowns[user_id]
            if now < cooldown_end:
                retry_after = int(cooldown_end - now) + 1
                return RateLimitResult(
                    allowed=False,
                    retry_after_seconds=retry_after,
                    message=f"Rate limited. Please wait {retry_after} seconds."
                )
            else:
                del self._cooldowns[user_id]
        
        # Clean up old entries
        self._message_timestamps[user_id] = self._cleanup_old_entries(
            self._message_timestamps[user_id], 3600  # Keep 1 hour of history
        )
        
        timestamps = self._message_timestamps[user_id]
        
        # Check per-minute limit
        one_minute_ago = now - 60
        recent_minute = sum(1 for ts in timestamps if ts > one_minute_ago)
        if recent_minute >= self.config.messages_per_minute:
            self._cooldowns[user_id] = now + self.config.cooldown_seconds
            return RateLimitResult(
                allowed=False,
                retry_after_seconds=self.config.cooldown_seconds,
                message=f"Too many messages. Please wait {self.config.cooldown_seconds} seconds."
            )
        
        # Check per-hour limit
        if len(timestamps) >= self.config.messages_per_hour:
            retry_after = int(timestamps[0] + 3600 - now) + 1
            return RateLimitResult(
                allowed=False,
                retry_after_seconds=retry_after,
                message=f"Hourly message limit reached. Please wait {retry_after} seconds."
            )
        
        return RateLimitResult(allowed=True)
    
    def check_generation_rate(self, user_id: int) -> RateLimitResult:
        """Check if user can perform a generation."""
        now = time()
        
        # First check message rate
        msg_result = self.check_message_rate(user_id)
        if not msg_result.allowed:
            return msg_result
        
        # Clean up old entries (keep 24 hours)
        self._generation_timestamps[user_id] = self._cleanup_old_entries(
            self._generation_timestamps[user_id], 86400
        )
        
        timestamps = self._generation_timestamps[user_id]
        
        # Check per-minute limit
        one_minute_ago = now - 60
        recent_minute = sum(1 for ts in timestamps if ts > one_minute_ago)
        if recent_minute >= self.config.generations_per_minute:
            retry_after = 60 - int(now - max(ts for ts in timestamps if ts > one_minute_ago))
            return RateLimitResult(
                allowed=False,
                retry_after_seconds=max(retry_after, 1),
                message=f"Generation rate limit reached. Please wait {max(retry_after, 1)} seconds."
            )
        
        # Check per-hour limit
        one_hour_ago = now - 3600
        recent_hour = sum(1 for ts in timestamps if ts > one_hour_ago)
        if recent_hour >= self.config.generations_per_hour:
            oldest_in_hour = min(ts for ts in timestamps if ts > one_hour_ago)
            retry_after = int(oldest_in_hour + 3600 - now) + 1
            return RateLimitResult(
                allowed=False,
                retry_after_seconds=retry_after,
                message=f"Hourly generation limit reached ({self.config.generations_per_hour}/hour). "
                        f"Please wait {retry_after} seconds."
            )
        
        # Check per-day limit
        if len(timestamps) >= self.config.generations_per_day:
            oldest = min(timestamps)
            retry_after = int(oldest + 86400 - now) + 1
            return RateLimitResult(
                allowed=False,
                retry_after_seconds=retry_after,
                message=f"Daily generation limit reached ({self.config.generations_per_day}/day). "
                        f"Resets in {retry_after // 3600} hours."
            )
        
        return RateLimitResult(allowed=True)
    
    def record_message(self, user_id: int) -> None:
        """Record a message from user."""
        self._message_timestamps[user_id].append(time())
    
    def record_generation(self, user_id: int) -> None:
        """Record a generation from user."""
        now = time()
        self._generation_timestamps[user_id].append(now)
        self._message_timestamps[user_id].append(now)
    
    def get_user_stats(self, user_id: int) -> dict[str, int]:
        """Get rate limit stats for a user."""
        now = time()
        
        msg_timestamps = self._cleanup_old_entries(
            self._message_timestamps.get(user_id, []), 3600
        )
        gen_timestamps = self._cleanup_old_entries(
            self._generation_timestamps.get(user_id, []), 86400
        )
        
        one_minute_ago = now - 60
        one_hour_ago = now - 3600
        
        return {
            "messages_last_minute": sum(1 for ts in msg_timestamps if ts > one_minute_ago),
            "messages_last_hour": len(msg_timestamps),
            "generations_last_minute": sum(1 for ts in gen_timestamps if ts > one_minute_ago),
            "generations_last_hour": sum(1 for ts in gen_timestamps if ts > one_hour_ago),
            "generations_last_day": len(gen_timestamps),
        }


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create the global rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
