import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from services.fal import FalService
from services.r2 import R2Service
import io
from PIL import Image

@pytest.fixture
def mock_fal_service():
    service = MagicMock(spec=FalService)

    # Generate a valid tiny JPEG image
    img = Image.new('RGB', (10, 10), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    valid_image_bytes = img_byte_arr.getvalue()

    service.generate_image = AsyncMock(return_value=valid_image_bytes)
    return service

@pytest.fixture
def mock_r2_service():
    service = MagicMock(spec=R2Service)
    service.upload_file = AsyncMock(return_value="test_image.jpg")
    return service
