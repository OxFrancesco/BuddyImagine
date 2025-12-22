import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from botocore.exceptions import ClientError
from imagine.services.r2 import R2Service


class TestUploadFile:
    @pytest.mark.asyncio
    async def test_upload_file_success(self):
        with patch("aioboto3.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value = mock_session

            mock_s3 = AsyncMock()
            mock_client_ctx = MagicMock()
            mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_s3)
            mock_client_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session.client.return_value = mock_client_ctx

            service = R2Service()
            service.access_key = "fake_key"
            service.secret_key = "fake_secret"
            service.bucket_name = "test-bucket"
            service.endpoint_url = "https://fake.r2.endpoint"

            result = await service.upload_file(b"test_data", "test.jpg")

            assert result == "test.jpg"
            mock_s3.put_object.assert_called_once_with(
                Bucket="test-bucket",
                Key="test.jpg",
                Body=b"test_data",
                ContentType="image/jpeg"
            )

    @pytest.mark.asyncio
    async def test_upload_file_custom_content_type(self):
        with patch("aioboto3.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value = mock_session

            mock_s3 = AsyncMock()
            mock_client_ctx = MagicMock()
            mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_s3)
            mock_client_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session.client.return_value = mock_client_ctx

            service = R2Service()
            service.access_key = "fake_key"
            service.secret_key = "fake_secret"
            service.bucket_name = "test-bucket"
            service.endpoint_url = "https://fake.r2.endpoint"

            result = await service.upload_file(b"test_data", "test.png", content_type="image/png")

            assert result == "test.png"
            mock_s3.put_object.assert_called_once_with(
                Bucket="test-bucket",
                Key="test.png",
                Body=b"test_data",
                ContentType="image/png"
            )

    @pytest.mark.asyncio
    async def test_upload_file_client_error(self):
        with patch("aioboto3.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value = mock_session

            mock_s3 = AsyncMock()
            mock_s3.put_object.side_effect = ClientError(
                {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
                "PutObject"
            )

            mock_client_ctx = MagicMock()
            mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_s3)
            mock_client_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session.client.return_value = mock_client_ctx

            service = R2Service()
            service.access_key = "fake_key"
            service.secret_key = "fake_secret"
            service.bucket_name = "test-bucket"
            service.endpoint_url = "https://fake.r2.endpoint"

            with pytest.raises(ClientError):
                await service.upload_file(b"test_data", "test.jpg")


class TestDownloadFile:
    @pytest.mark.asyncio
    async def test_download_file_success(self):
        with patch("aioboto3.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value = mock_session

            mock_body = MagicMock()
            mock_body.read = AsyncMock(return_value=b"downloaded_data")

            mock_s3 = AsyncMock()
            mock_s3.get_object.return_value = {"Body": mock_body}

            mock_client_ctx = MagicMock()
            mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_s3)
            mock_client_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session.client.return_value = mock_client_ctx

            service = R2Service()
            service.access_key = "fake_key"
            service.secret_key = "fake_secret"
            service.bucket_name = "test-bucket"
            service.endpoint_url = "https://fake.r2.endpoint"

            result = await service.download_file("test.jpg")

            assert result == b"downloaded_data"
            mock_s3.get_object.assert_called_once_with(
                Bucket="test-bucket",
                Key="test.jpg"
            )

    @pytest.mark.asyncio
    async def test_download_file_not_found(self):
        with patch("aioboto3.Session") as MockSession:
            mock_session = MagicMock()
            MockSession.return_value = mock_session

            mock_s3 = AsyncMock()
            mock_s3.get_object.side_effect = ClientError(
                {"Error": {"Code": "NoSuchKey", "Message": "The specified key does not exist."}},
                "GetObject"
            )

            mock_client_ctx = MagicMock()
            mock_client_ctx.__aenter__ = AsyncMock(return_value=mock_s3)
            mock_client_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session.client.return_value = mock_client_ctx

            service = R2Service()
            service.access_key = "fake_key"
            service.secret_key = "fake_secret"
            service.bucket_name = "test-bucket"
            service.endpoint_url = "https://fake.r2.endpoint"

            with pytest.raises(ClientError) as exc_info:
                await service.download_file("nonexistent.jpg")
            
            assert exc_info.value.response["Error"]["Code"] == "NoSuchKey"
