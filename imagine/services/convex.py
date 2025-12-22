import os
from typing import Any, TypedDict
from convex import ConvexClient
from dotenv import load_dotenv

# Load .env.local if it exists (created by npx convex dev)
load_dotenv(".env.local")
load_dotenv()


class UserSettingsDict(TypedDict, total=False):
    telegram_id: int
    credits: float
    default_model: str
    save_uncompressed_to_r2: bool
    telegram_quality: str
    notify_low_credits: bool
    low_credit_threshold: float
    last_generated_image: str | None


class CreditResultDict(TypedDict, total=False):
    success: bool
    message: str
    current_credits: float


class CreditLogDict(TypedDict):
    amount: float
    balance_after: float
    type: str
    description: str
    model_used: str | None
    r2_filename: str | None
    created_at: int


class CreditSummaryDict(TypedDict):
    current_balance: float
    total_spent: float
    total_added: float
    generation_count: int


class MessageDict(TypedDict):
    role: str
    content: str
    created_at: int


class ConvexService:
    """Service for interacting with Convex database."""
    
    def __init__(self) -> None:
        convex_url = os.getenv("CONVEX_URL")
        if not convex_url:
            raise ValueError("CONVEX_URL environment variable is not set")
        self.client = ConvexClient(convex_url)

    def upsert_user(
        self,
        telegram_id: int,
        first_name: str,
        username: str | None = None,
        last_name: str | None = None,
        default_model: str | None = None,
    ) -> str:
        """Create or update a user. Returns user ID."""
        args: dict[str, Any] = {
            "telegram_id": telegram_id,
            "first_name": first_name,
        }
        if username is not None:
            args["username"] = username
        if last_name is not None:
            args["last_name"] = last_name
        if default_model is not None:
            args["default_model"] = default_model
            
        return str(self.client.mutation("users:upsertUser", args))

    def set_default_model(self, telegram_id: int, model_id: str) -> dict[str, Any]:
        """Set user's default model."""
        return dict(self.client.mutation("users:setDefaultModel", {"telegram_id": telegram_id, "model_id": model_id}))

    def get_user(self, telegram_id: int) -> dict[str, Any] | None:
        """Get user by telegram ID."""
        result = self.client.query("users:getUser", {"telegram_id": telegram_id})
        return dict(result) if result else None

    def deduct_credits(self, telegram_id: int, amount: float) -> CreditResultDict:
        """Deduct credits from user."""
        result = self.client.mutation("users:deductCredits", {"telegram_id": telegram_id, "amount": amount})
        return dict(result) if result else {"success": False}  # type: ignore

    def refund_credits(self, telegram_id: int, amount: float) -> CreditResultDict:
        """Refund credits to user."""
        result = self.client.mutation("users:refundCredits", {"telegram_id": telegram_id, "amount": amount})
        return dict(result) if result else {"success": False}  # type: ignore

    def get_credits(self, telegram_id: int) -> float:
        """Get user's current credit balance."""
        result = self.client.query("users:getCredits", {"telegram_id": telegram_id})
        return float(result) if result is not None else 0.0

    def save_message(self, telegram_id: int, role: str, content: str) -> str:
        """Save a message to conversation history. Returns message ID."""
        return str(self.client.mutation("messages:saveMessage", {
            "telegram_id": telegram_id,
            "role": role,
            "content": content,
        }))

    def get_messages(self, telegram_id: int, limit: int = 20) -> list[MessageDict]:
        """Get conversation history for a user."""
        result = self.client.query("messages:getMessages", {
            "telegram_id": telegram_id,
            "limit": limit,
        })
        return list(result) if result else []  # type: ignore

    def clear_messages(self, telegram_id: int) -> dict[str, int]:
        """Clear all messages for a user. Returns count of deleted messages."""
        result = self.client.mutation("messages:clearMessages", {"telegram_id": telegram_id})
        return dict(result) if result else {"deleted": 0}  # type: ignore

    # User Settings Methods
    def update_user_settings(
        self,
        telegram_id: int,
        save_uncompressed_to_r2: bool | None = None,
        telegram_quality: str | None = None,
        notify_low_credits: bool | None = None,
        low_credit_threshold: float | None = None,
    ) -> dict[str, bool]:
        """Update user settings."""
        args: dict[str, Any] = {"telegram_id": telegram_id}
        if save_uncompressed_to_r2 is not None:
            args["save_uncompressed_to_r2"] = save_uncompressed_to_r2
        if telegram_quality is not None:
            args["telegram_quality"] = telegram_quality
        if notify_low_credits is not None:
            args["notify_low_credits"] = notify_low_credits
        if low_credit_threshold is not None:
            args["low_credit_threshold"] = low_credit_threshold
        result = self.client.mutation("users:updateUserSettings", args)
        return dict(result) if result else {"success": False}  # type: ignore

    def get_user_settings(self, telegram_id: int) -> UserSettingsDict | None:
        """Get user settings."""
        result = self.client.query("users:getUserSettings", {"telegram_id": telegram_id})
        return dict(result) if result else None  # type: ignore

    # Credit Logging Methods
    def deduct_credits_with_log(
        self,
        telegram_id: int,
        amount: float,
        log_type: str,
        description: str,
        model_used: str | None = None,
        r2_filename: str | None = None,
    ) -> CreditResultDict:
        """Deduct credits and log the transaction."""
        args: dict[str, Any] = {
            "telegram_id": telegram_id,
            "amount": amount,
            "type": log_type,
            "description": description,
        }
        if model_used is not None:
            args["model_used"] = model_used
        if r2_filename is not None:
            args["r2_filename"] = r2_filename
        result = self.client.mutation("users:deductCreditsWithLog", args)
        return dict(result) if result else {"success": False}  # type: ignore

    def add_credits_with_log(
        self,
        telegram_id: int,
        amount: float,
        log_type: str,
        description: str,
    ) -> CreditResultDict:
        """Add credits and log the transaction."""
        result = self.client.mutation("users:addCreditsWithLog", {
            "telegram_id": telegram_id,
            "amount": amount,
            "type": log_type,
            "description": description,
        })
        return dict(result) if result else {"success": False}  # type: ignore

    def get_credit_history(self, telegram_id: int, limit: int = 50) -> list[CreditLogDict]:
        """Get credit transaction history."""
        result = self.client.query("creditLogs:getCreditHistory", {
            "telegram_id": telegram_id,
            "limit": limit,
        })
        return list(result) if result else []  # type: ignore

    def get_credit_summary(self, telegram_id: int) -> CreditSummaryDict | None:
        """Get credit summary statistics."""
        result = self.client.query("creditLogs:getCreditSummary", {"telegram_id": telegram_id})
        return dict(result) if result else None  # type: ignore

    def set_last_generated_image(self, telegram_id: int, filename: str) -> dict[str, bool]:
        """Set the last generated image filename for a user."""
        result = self.client.mutation("users:setLastGeneratedImage", {
            "telegram_id": telegram_id,
            "filename": filename,
        })
        return dict(result) if result else {"success": False}  # type: ignore

    def get_last_generated_image(self, telegram_id: int) -> str | None:
        """Get the last generated image filename for a user."""
        result = self.client.query("users:getLastGeneratedImage", {"telegram_id": telegram_id})
        return str(result) if result else None
