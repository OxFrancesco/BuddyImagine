import os
from typing import Any
from convex import ConvexClient
from dotenv import load_dotenv

# Load .env.local if it exists (created by npx convex dev)
load_dotenv(".env.local")
load_dotenv()

class ConvexService:
    def __init__(self):
        convex_url = os.getenv("CONVEX_URL")
        if not convex_url:
            raise ValueError("CONVEX_URL environment variable is not set")
        self.client = ConvexClient(convex_url)

    def upsert_user(self, telegram_id: int, first_name: str, username: str | None = None, last_name: str | None = None, default_model: str | None = None):
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
            
        return self.client.mutation("users:upsertUser", args)

    def set_default_model(self, telegram_id: int, model_id: str):
        return self.client.mutation("users:setDefaultModel", {"telegram_id": telegram_id, "model_id": model_id})

    def get_user(self, telegram_id: int):
        return self.client.query("users:getUser", {"telegram_id": telegram_id})

    def deduct_credits(self, telegram_id: int, amount: float):
        return self.client.mutation("users:deductCredits", {"telegram_id": telegram_id, "amount": amount})

    def refund_credits(self, telegram_id: int, amount: float):
        return self.client.mutation("users:refundCredits", {"telegram_id": telegram_id, "amount": amount})

    def get_credits(self, telegram_id: int) -> float:
        return float(self.client.query("users:getCredits", {"telegram_id": telegram_id}))

    def save_message(self, telegram_id: int, role: str, content: str):
        return self.client.mutation("messages:saveMessage", {
            "telegram_id": telegram_id,
            "role": role,
            "content": content,
        })

    def get_messages(self, telegram_id: int, limit: int = 20) -> list[Any]:
        result = self.client.query("messages:getMessages", {
            "telegram_id": telegram_id,
            "limit": limit,
        })
        return list(result) if result else []

    def clear_messages(self, telegram_id: int):
        return self.client.mutation("messages:clearMessages", {"telegram_id": telegram_id})

    # User Settings Methods
    def update_user_settings(
        self,
        telegram_id: int,
        save_uncompressed_to_r2: bool | None = None,
        telegram_quality: str | None = None,
        notify_low_credits: bool | None = None,
        low_credit_threshold: float | None = None,
    ):
        args: dict[str, Any] = {"telegram_id": telegram_id}
        if save_uncompressed_to_r2 is not None:
            args["save_uncompressed_to_r2"] = save_uncompressed_to_r2
        if telegram_quality is not None:
            args["telegram_quality"] = telegram_quality
        if notify_low_credits is not None:
            args["notify_low_credits"] = notify_low_credits
        if low_credit_threshold is not None:
            args["low_credit_threshold"] = low_credit_threshold
        return self.client.mutation("users:updateUserSettings", args)

    def get_user_settings(self, telegram_id: int) -> dict[str, Any] | None:
        result = self.client.query("users:getUserSettings", {"telegram_id": telegram_id})
        return dict(result) if result else None

    # Credit Logging Methods
    def deduct_credits_with_log(
        self,
        telegram_id: int,
        amount: float,
        log_type: str,
        description: str,
        model_used: str | None = None,
        r2_filename: str | None = None,
    ):
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
        return self.client.mutation("users:deductCreditsWithLog", args)

    def add_credits_with_log(
        self,
        telegram_id: int,
        amount: float,
        log_type: str,
        description: str,
    ):
        return self.client.mutation("users:addCreditsWithLog", {
            "telegram_id": telegram_id,
            "amount": amount,
            "type": log_type,
            "description": description,
        })

    def get_credit_history(self, telegram_id: int, limit: int = 50) -> list[Any]:
        result = self.client.query("creditLogs:getCreditHistory", {
            "telegram_id": telegram_id,
            "limit": limit,
        })
        return list(result) if result else []

    def get_credit_summary(self, telegram_id: int) -> dict[str, Any] | None:
        result = self.client.query("creditLogs:getCreditSummary", {"telegram_id": telegram_id})
        return dict(result) if result else None
