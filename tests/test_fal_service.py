import pytest
import base64
from unittest.mock import AsyncMock, MagicMock, patch
from imagine.services.fal import FalService


class TestSearchModels:
    def test_search_models_empty_query(self):
        service = FalService()
        results = service.search_models("", limit=5)
        assert len(results) == 5
        assert results == service.KNOWN_MODELS[:5]

    def test_search_models_exact_match(self):
        service = FalService()
        results = service.search_models("flux", limit=5)
        assert len(results) > 0
        assert any("flux" in m["id"].lower() for m in results)

    def test_search_models_fuzzy_match(self):
        service = FalService()
        results = service.search_models("banana", limit=5)
        assert len(results) > 0
        assert any("banana" in m["id"].lower() for m in results)

    def test_search_models_no_match(self):
        service = FalService()
        results = service.search_models("xyznonexistent123", limit=5)
        assert len(results) == 0

    def test_search_models_limit(self):
        service = FalService()
        results = service.search_models("", limit=2)
        assert len(results) == 2

    def test_search_models_description_match(self):
        service = FalService()
        results = service.search_models("typography", limit=5)
        assert len(results) > 0
        assert any("ideogram" in m["id"].lower() for m in results)


class TestEstimateCost:
    def test_estimate_cost_known_model(self):
        service = FalService()
        cost = service.estimate_cost("fal-ai/fast-sdxl")
        assert cost == 0.005

    def test_estimate_cost_flux_dev(self):
        service = FalService()
        cost = service.estimate_cost("fal-ai/flux/dev")
        assert cost == 0.03

    def test_estimate_cost_video_model(self):
        service = FalService()
        cost = service.estimate_cost("fal-ai/hunyuan-video-v1.5/text-to-video")
        assert cost == 0.50

    def test_estimate_cost_unknown_model(self):
        service = FalService()
        cost = service.estimate_cost("unknown/model")
        assert cost == service.DEFAULT_COST


class TestGenerateImage:
    @pytest.mark.asyncio
    async def test_generate_image_success_with_url(self):
        with patch("aiohttp.ClientSession") as MockSession:
            mock_session = MagicMock()
            mock_session_ctx = MagicMock()
            mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
            MockSession.return_value = mock_session_ctx

            mock_post_response = MagicMock()
            mock_post_response.status = 200
            mock_post_response.headers = {"Content-Type": "application/json"}
            mock_post_response.json = AsyncMock(return_value={
                "images": [{"url": "http://fake.url/image.jpg"}]
            })

            mock_post_ctx = MagicMock()
            mock_post_ctx.__aenter__ = AsyncMock(return_value=mock_post_response)
            mock_post_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session.post.return_value = mock_post_ctx

            mock_get_response = MagicMock()
            mock_get_response.status = 200
            mock_get_response.read = AsyncMock(return_value=b"image_bytes")

            mock_get_ctx = MagicMock()
            mock_get_ctx.__aenter__ = AsyncMock(return_value=mock_get_response)
            mock_get_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session.get.return_value = mock_get_ctx

            service = FalService()
            service.fal_key = "fake_key"

            result = await service.generate_image("test prompt")
            assert result == b"image_bytes"

    @pytest.mark.asyncio
    async def test_generate_image_base64_response(self):
        with patch("aiohttp.ClientSession") as MockSession:
            mock_session = MagicMock()
            mock_session_ctx = MagicMock()
            mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
            MockSession.return_value = mock_session_ctx

            image_bytes = b"fake_image_data"
            base64_data = base64.b64encode(image_bytes).decode()
            data_uri = f"data:image/jpeg;base64,{base64_data}"

            mock_post_response = MagicMock()
            mock_post_response.status = 200
            mock_post_response.headers = {"Content-Type": "application/json"}
            mock_post_response.json = AsyncMock(return_value={
                "images": [{"url": data_uri}]
            })

            mock_post_ctx = MagicMock()
            mock_post_ctx.__aenter__ = AsyncMock(return_value=mock_post_response)
            mock_post_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session.post.return_value = mock_post_ctx

            service = FalService()
            service.fal_key = "fake_key"

            result = await service.generate_image("test prompt")
            assert result == image_bytes

    @pytest.mark.asyncio
    async def test_generate_image_api_error(self):
        with patch("aiohttp.ClientSession") as MockSession:
            mock_session = MagicMock()
            mock_session_ctx = MagicMock()
            mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
            MockSession.return_value = mock_session_ctx

            mock_post_response = MagicMock()
            mock_post_response.status = 500
            mock_post_response.text = AsyncMock(return_value="Internal Server Error")
            mock_post_response.headers = {"Content-Type": "application/json"}

            mock_post_ctx = MagicMock()
            mock_post_ctx.__aenter__ = AsyncMock(return_value=mock_post_response)
            mock_post_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session.post.return_value = mock_post_ctx

            service = FalService()
            service.fal_key = "fake_key"

            with pytest.raises(Exception) as exc_info:
                await service.generate_image("test prompt")
            assert "500" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_image_direct_binary_response(self):
        with patch("aiohttp.ClientSession") as MockSession:
            mock_session = MagicMock()
            mock_session_ctx = MagicMock()
            mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
            MockSession.return_value = mock_session_ctx

            mock_post_response = MagicMock()
            mock_post_response.status = 200
            mock_post_response.headers = {"Content-Type": "image/jpeg"}
            mock_post_response.read = AsyncMock(return_value=b"direct_image_bytes")

            mock_post_ctx = MagicMock()
            mock_post_ctx.__aenter__ = AsyncMock(return_value=mock_post_response)
            mock_post_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session.post.return_value = mock_post_ctx

            service = FalService()
            service.fal_key = "fake_key"

            result = await service.generate_image("test prompt")
            assert result == b"direct_image_bytes"

    @pytest.mark.asyncio
    async def test_generate_image_with_custom_model(self):
        with patch("aiohttp.ClientSession") as MockSession:
            mock_session = MagicMock()
            mock_session_ctx = MagicMock()
            mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_ctx.__aexit__ = AsyncMock(return_value=None)
            MockSession.return_value = mock_session_ctx

            mock_post_response = MagicMock()
            mock_post_response.status = 200
            mock_post_response.headers = {"Content-Type": "image/png"}
            mock_post_response.read = AsyncMock(return_value=b"image_bytes")

            mock_post_ctx = MagicMock()
            mock_post_ctx.__aenter__ = AsyncMock(return_value=mock_post_response)
            mock_post_ctx.__aexit__ = AsyncMock(return_value=None)
            mock_session.post.return_value = mock_post_ctx

            service = FalService()
            service.fal_key = "fake_key"

            await service.generate_image("test prompt", model="fal-ai/flux/dev")
            
            call_args = mock_session.post.call_args
            assert "fal-ai/flux/dev" in call_args[0][0]
