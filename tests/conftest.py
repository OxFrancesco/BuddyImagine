import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from imagine.services.fal import FalService
from imagine.services.r2 import R2Service
import io
from PIL import Image


def create_valid_image_bytes() -> bytes:
    """Create valid JPEG image bytes for testing."""
    img = Image.new('RGB', (10, 10), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    return img_byte_arr.getvalue()


@pytest.fixture
def mock_fal_service():
    service = MagicMock(spec=FalService)
    service.generate_image = AsyncMock(return_value=create_valid_image_bytes())
    service.search_models = MagicMock(return_value=[
        {"id": "fal-ai/fast-sdxl", "name": "Fast SDXL", "description": "Fast Stable Diffusion XL"}
    ])
    service.estimate_cost = MagicMock(return_value=0.005)
    service.KNOWN_MODELS = FalService.KNOWN_MODELS
    service.PRICING_TABLE = FalService.PRICING_TABLE
    service.DEFAULT_COST = FalService.DEFAULT_COST
    return service


@pytest.fixture
def mock_r2_service():
    service = MagicMock(spec=R2Service)
    service.upload_file = AsyncMock(return_value="test_image.jpg")
    service.download_file = AsyncMock(return_value=create_valid_image_bytes())
    return service


@pytest.fixture
def mock_convex_service():
    with patch("imagine.services.convex.ConvexClient"):
        service = MagicMock()
        service.upsert_user = MagicMock(return_value="user_id_123")
        service.get_user = MagicMock(return_value={
            "telegram_id": 12345,
            "first_name": "Test",
            "credits": 100.0,
            "default_model": "fal-ai/fast-sdxl"
        })
        service.set_default_model = MagicMock()
        service.deduct_credits = MagicMock(return_value={"success": True, "current_credits": 95.0})
        service.refund_credits = MagicMock()
        service.get_credits = MagicMock(return_value=100.0)
        service.save_message = MagicMock()
        service.get_messages = MagicMock(return_value=[])
        service.clear_messages = MagicMock(return_value={"deleted": 0})
        service.update_user_settings = MagicMock()
        service.get_user_settings = MagicMock(return_value={
            "telegram_quality": "uncompressed",
            "save_uncompressed_to_r2": False,
            "notify_low_credits": True,
            "low_credit_threshold": 10.0,
            "credits": 100.0
        })
        service.deduct_credits_with_log = MagicMock(return_value={"success": True, "current_credits": 95.0})
        service.add_credits_with_log = MagicMock()
        service.get_credit_history = MagicMock(return_value=[])
        service.get_credit_summary = MagicMock(return_value={
            "current_balance": 100.0,
            "total_spent": 0.0,
            "total_added": 100.0,
            "generation_count": 0
        })
        return service
