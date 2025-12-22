import pytest
import os
from imagine.services.convex import ConvexService
from dotenv import load_dotenv

load_dotenv(".env.local")
load_dotenv()

@pytest.mark.skipif(not os.getenv("CONVEX_URL"), reason="CONVEX_URL not set")
def test_convex_user_flow():
    service = ConvexService()
    
    # Test data
    telegram_id = 123456789012345 # Larger int to ensure it's treated as int64
    username = "test_user"
    first_name = "Test"
    last_name = "User"
    
    # 1. Upsert user
    user_id = service.upsert_user(telegram_id, first_name, username, last_name)
    assert user_id is not None
    
    # 2. Get user
    user = service.get_user(telegram_id)
    assert user is not None
    assert user["telegram_id"] == telegram_id
    assert user["username"] == username
    assert user["first_name"] == first_name
    assert user["last_name"] == last_name
    
    # 3. Update user
    new_first_name = "Updated"
    service.upsert_user(telegram_id, new_first_name, username, last_name)
    
    updated_user = service.get_user(telegram_id)
    assert updated_user["first_name"] == new_first_name

    # 4. Test Credit Deduction
    initial_credits = service.get_credits(telegram_id)
    assert initial_credits > 0
    
    # Test default model
    default_model = "fal-ai/flux/dev"
    service.set_default_model(telegram_id, default_model)
    
    user = service.get_user(telegram_id)
    assert user["default_model"] == default_model
    
    print("Convex integration tests passed!")
    deduct_amount = 5.0
    result = service.deduct_credits(telegram_id, deduct_amount)
    assert result["success"] is True
    assert result["current_credits"] == initial_credits - deduct_amount
    
    # 5. Test Insufficient Credits
    huge_amount = 1000000.0
    result = service.deduct_credits(telegram_id, huge_amount)
    assert result["success"] is False
    
    # 6. Test Refund
    refund_amount = 5.0
    service.refund_credits(telegram_id, refund_amount)
    final_credits = service.get_credits(telegram_id)
    assert final_credits == initial_credits
