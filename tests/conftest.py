import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from services.fal import FalService
from services.r2 import R2Service

@pytest.fixture
def mock_fal_service():
    service = MagicMock(spec=FalService)
    service.generate_image = AsyncMock(return_value=b"fake_image_data")
    return service

@pytest.fixture
def mock_r2_service():
    service = MagicMock(spec=R2Service)
    service.upload_file = AsyncMock(return_value="test_image.jpg")
    return service
