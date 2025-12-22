"""Pydantic models for input validation and type safety."""

from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator
import re


class UserSettings(BaseModel):
    """User preference settings."""
    telegram_quality: Literal["compressed", "uncompressed"] = "uncompressed"
    save_uncompressed_to_r2: bool = False
    notify_low_credits: bool = True
    low_credit_threshold: float = Field(default=10.0, ge=0, le=10000)


class GenerationRequest(BaseModel):
    """Validated image generation request."""
    prompt: str = Field(..., min_length=1, max_length=2000)
    model_id: Optional[str] = Field(default=None, max_length=100)

    @field_validator("prompt")
    @classmethod
    def sanitize_prompt(cls, v: str) -> str:
        # Strip whitespace
        v = v.strip()
        # Check if empty after stripping
        if not v:
            raise ValueError("Prompt cannot be empty or whitespace only")
        # Remove excessive whitespace
        v = re.sub(r"\s+", " ", v)
        return v

    @field_validator("model_id")
    @classmethod
    def validate_model_id(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        v = v.strip()
        # Model IDs should match fal-ai pattern
        if v and not re.match(r"^[a-zA-Z0-9\-_/]+$", v):
            raise ValueError("Invalid model ID format")
        return v


class CreditTransaction(BaseModel):
    """Credit transaction record."""
    amount: float = Field(..., gt=0, le=100000)
    log_type: Literal["generation", "refund", "purchase", "admin", "subscription"]
    description: str = Field(..., min_length=1, max_length=500)
    model_used: Optional[str] = None
    r2_filename: Optional[str] = None


class UserProfile(BaseModel):
    """User profile data from Convex."""
    telegram_id: int
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    credits: float = Field(ge=0)
    default_model: str = "fal-ai/fast-sdxl"
    save_uncompressed_to_r2: bool = False
    telegram_quality: Literal["compressed", "uncompressed"] = "uncompressed"
    notify_low_credits: bool = True
    low_credit_threshold: float = 10.0


class CreditSummary(BaseModel):
    """Credit summary statistics."""
    current_balance: float
    total_spent: float
    total_added: float
    generation_count: int


class CreditLog(BaseModel):
    """Single credit log entry."""
    amount: float
    balance_after: float
    type: str
    description: str
    model_used: Optional[str] = None
    r2_filename: Optional[str] = None
    created_at: int


class RateLimitResult(BaseModel):
    """Result of a rate limit check."""
    allowed: bool
    retry_after_seconds: Optional[int] = None
    message: Optional[str] = None
