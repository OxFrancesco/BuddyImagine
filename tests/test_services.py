import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.fal import FalService
from services.r2 import R2Service

@pytest.mark.asyncio
async def test_fal_service_generate_image():
    with patch("aiohttp.ClientSession") as MockSession:
        mock_session = MagicMock()
        
        # MockSession() returns the context manager
        mock_session_ctx = MagicMock()
        mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
        MockSession.return_value = mock_session_ctx
        
        # Mock POST response (generation request)
        mock_post_response = MagicMock()
        mock_post_response.status = 200
        mock_post_response.json = AsyncMock(return_value={"images": [{"url": "http://fake.url/image.jpg"}]})
        mock_post_response.text = AsyncMock(return_value="")
        
        # session.post() returns an async context manager
        mock_post_ctx = MagicMock()
        mock_post_ctx.__aenter__ = AsyncMock(return_value=mock_post_response)
        mock_post_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_session.post.return_value = mock_post_ctx
        
        # Mock GET response (image download)
        mock_get_response = MagicMock()
        mock_get_response.status = 200
        mock_get_response.read = AsyncMock(return_value=b"image_bytes")
        
        # session.get() returns an async context manager
        mock_get_ctx = MagicMock()
        mock_get_ctx.__aenter__ = AsyncMock(return_value=mock_get_response)
        mock_get_ctx.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_get_ctx
        
        service = FalService()
        # Inject fake credentials to avoid warning/error in init if env vars missing
        service.fal_key = "fake"
        service.base_url = "http://fake.base"

        result = await service.generate_image("test prompt")
        assert result == b"image_bytes"

@pytest.mark.asyncio
async def test_r2_service_upload_file():
    with patch("aioboto3.Session") as MockSession:
        mock_session = MagicMock()
        MockSession.return_value = mock_session
        
        mock_s3 = AsyncMock()
        mock_session.client.return_value.__aenter__.return_value = mock_s3
        
        service = R2Service()
        service.access_key = "fake"
        service.secret_key = "fake"
        service.bucket_name = "fake-bucket"
        service.endpoint_url = "http://fake.endpoint"

        result = await service.upload_file(b"data", "test.jpg")
        
        assert result == "test.jpg"
        mock_s3.put_object.assert_called_once_with(
            Bucket="fake-bucket",
            Key="test.jpg",
            Body=b"data",
            ContentType="image/jpeg"
        )
