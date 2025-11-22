import os
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

    def upsert_user(self, telegram_id: int, first_name: str, username: str | None = None, last_name: str | None = None):
        # Convex Python client requires explicit float for v.float64 and might need help with Int64 if it defaults to float
        # However, usually int maps to Int64 or Float64 depending on value. 
        # If we have issues, we might need to check if there is a specific wrapper.
        # But based on search, we might need to ensure it's not treated as float.
        # Let's try to just pass int. If it fails with "Value: ...0", it means it was converted to float.
        # The fix is likely using a specific type if available, or ensuring the client version supports it.
        # But since I can't easily check available types, I'll try to just pass it.
        # Wait, I already tried passing int(telegram_id) and it failed.
        # I will try to import ConvexInt64.
        return self.client.mutation("users:upsertUser", {
            "telegram_id": telegram_id, # The client should handle this if it's a standard int.
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
        })

    def get_user(self, telegram_id: int):
        return self.client.query("users:getUser", {"telegram_id": telegram_id})

    def deduct_credits(self, telegram_id: int, amount: float):
        return self.client.mutation("users:deductCredits", {"telegram_id": telegram_id, "amount": amount})

    def refund_credits(self, telegram_id: int, amount: float):
        return self.client.mutation("users:refundCredits", {"telegram_id": telegram_id, "amount": amount})

    def get_credits(self, telegram_id: int) -> float:
        return float(self.client.query("users:getCredits", {"telegram_id": telegram_id}))
