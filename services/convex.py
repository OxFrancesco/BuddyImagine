import os
from typing import Any, Dict
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
        args: Dict[str, Any] = {
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
