import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import cast
import io
from PIL import Image
from pydantic_ai import RunContext
from imagine.agent import generate_and_save_image, search_available_models, ask_user_clarification, discover_fal_models
from imagine.services.fal import FalService


def create_valid_image_bytes() -> bytes:
    """Create valid JPEG image bytes for testing."""
    img = Image.new('RGB', (10, 10), color='red')
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    return img_byte_arr.getvalue()


class TestDiscoverFalModels:
    @pytest.mark.asyncio
    async def test_discover_models_with_query(self):
        mock_fal = MagicMock(spec=FalService)
        mock_fal.search_models.return_value = [
            {"id": "fal-ai/flux/dev", "name": "Flux Dev", "description": "Flux.1 Dev - High quality", "type": "text-to-image"}
        ]
        mock_fal.estimate_cost.return_value = 0.03

        mock_ctx = MagicMock()
        mock_ctx.deps = {"fal_service": mock_fal}

        result = await discover_fal_models(cast(RunContext[dict], mock_ctx), "flux")

        assert "flux" in result.lower()
        assert "fal-ai/flux/dev" in result
        assert "ID=" in result
        assert "Cost=" in result
        mock_fal.search_models.assert_called_once_with("flux", limit=5, model_type=None)

    @pytest.mark.asyncio
    async def test_discover_models_with_type_filter(self):
        mock_fal = MagicMock(spec=FalService)
        mock_fal.search_models.return_value = [
            {"id": "fal-ai/flux/dev/image-to-image", "name": "Flux Dev Img2Img", "description": "Image to image", "type": "image-to-image"}
        ]
        mock_fal.estimate_cost.return_value = 0.04

        mock_ctx = MagicMock()
        mock_ctx.deps = {"fal_service": mock_fal}

        result = await discover_fal_models(
            cast(RunContext[dict], mock_ctx), 
            "flux", 
            model_type="image-to-image"
        )

        assert "fal-ai/flux/dev/image-to-image" in result
        mock_fal.search_models.assert_called_once_with("flux", limit=5, model_type="image-to-image")

    @pytest.mark.asyncio
    async def test_discover_models_no_match(self):
        mock_fal = MagicMock(spec=FalService)
        mock_fal.search_models.return_value = []
        mock_fal.KNOWN_MODELS = [
            {"id": "fal-ai/fast-sdxl", "name": "Fast SDXL", "description": "Fast"},
            {"id": "fal-ai/flux/dev", "name": "Flux Dev", "description": "Flux"}
        ]

        mock_ctx = MagicMock()
        mock_ctx.deps = {"fal_service": mock_fal}

        result = await discover_fal_models(cast(RunContext[dict], mock_ctx), "nonexistent")

        assert "No models found" in result
        assert "nonexistent" in result

    @pytest.mark.asyncio
    async def test_discover_models_includes_cost_estimate(self):
        mock_fal = MagicMock(spec=FalService)
        mock_fal.search_models.return_value = [
            {"id": "fal-ai/flux/dev", "name": "Flux Dev", "description": "High quality", "type": "text-to-image"},
        ]
        mock_fal.estimate_cost.return_value = 0.03  # $0.03 -> ~0.345 credits

        mock_ctx = MagicMock()
        mock_ctx.deps = {"fal_service": mock_fal}

        result = await discover_fal_models(cast(RunContext[dict], mock_ctx), "flux")

        assert "credits" in result.lower()
        mock_fal.estimate_cost.assert_called_with("fal-ai/flux/dev")


class TestSearchAvailableModels:
    @pytest.mark.asyncio
    async def test_search_available_models_with_query(self):
        mock_fal = MagicMock(spec=FalService)
        mock_fal.search_models.return_value = [
            {"id": "fal-ai/flux/dev", "name": "Flux Dev", "description": "Flux.1 Dev - High quality"}
        ]

        mock_ctx = MagicMock()
        mock_ctx.deps = {"fal_service": mock_fal}

        result = await search_available_models(cast(RunContext[dict], mock_ctx), "flux")

        assert "flux" in result.lower()
        assert "fal-ai/flux/dev" in result
        mock_fal.search_models.assert_called_once_with("flux", limit=5)

    @pytest.mark.asyncio
    async def test_search_available_models_no_match(self):
        mock_fal = MagicMock(spec=FalService)
        mock_fal.search_models.return_value = []
        mock_fal.KNOWN_MODELS = [
            {"id": "fal-ai/fast-sdxl", "name": "Fast SDXL", "description": "Fast"},
            {"id": "fal-ai/flux/dev", "name": "Flux Dev", "description": "Flux"}
        ]

        mock_ctx = MagicMock()
        mock_ctx.deps = {"fal_service": mock_fal}

        result = await search_available_models(cast(RunContext[dict], mock_ctx), "nonexistent")

        assert "No models found" in result
        assert "nonexistent" in result

    @pytest.mark.asyncio
    async def test_search_available_models_multiple_results(self):
        mock_fal = MagicMock(spec=FalService)
        mock_fal.search_models.return_value = [
            {"id": "fal-ai/flux/dev", "name": "Flux Dev", "description": "High quality"},
            {"id": "fal-ai/flux/schnell", "name": "Flux Schnell", "description": "Fast"}
        ]

        mock_ctx = MagicMock()
        mock_ctx.deps = {"fal_service": mock_fal}

        result = await search_available_models(cast(RunContext[dict], mock_ctx), "flux")

        assert "2 model(s)" in result
        assert "fal-ai/flux/dev" in result
        assert "fal-ai/flux/schnell" in result


class TestAskUserClarification:
    @pytest.mark.asyncio
    async def test_ask_user_clarification_with_options(self):
        mock_ctx = MagicMock()

        result = await ask_user_clarification(
            cast(RunContext[dict], mock_ctx),
            "Which model do you prefer?",
            options=["fal-ai/flux/dev", "fal-ai/flux/schnell"]
        )

        assert result.startswith("CLARIFICATION_NEEDED|")
        assert "Which model do you prefer?" in result
        assert "fal-ai/flux/dev" in result
        assert "fal-ai/flux/schnell" in result

    @pytest.mark.asyncio
    async def test_ask_user_clarification_without_options(self):
        mock_ctx = MagicMock()

        result = await ask_user_clarification(
            cast(RunContext[dict], mock_ctx),
            "What style do you want?"
        )

        assert result == "CLARIFICATION_NEEDED|What style do you want?|"


class TestGenerateAndSaveImage:
    @pytest.mark.asyncio
    async def test_generate_and_save_image_default_model(self):
        mock_fal = MagicMock(spec=FalService)
        mock_fal.generate_image = AsyncMock(return_value=create_valid_image_bytes())
        mock_fal.search_models.return_value = []

        mock_r2 = MagicMock()
        mock_r2.upload_file = AsyncMock(return_value="test.jpg")

        mock_ctx = MagicMock()
        mock_ctx.deps = {"fal_service": mock_fal, "r2_service": mock_r2}

        result = await generate_and_save_image(
            cast(RunContext[dict], mock_ctx),
            "a beautiful sunset"
        )

        assert result.endswith(".jpg|fal-ai/fast-sdxl")
        mock_fal.generate_image.assert_called_once_with("a beautiful sunset")
        mock_r2.upload_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_and_save_image_with_explicit_model(self):
        mock_fal = MagicMock(spec=FalService)
        mock_fal.generate_image = AsyncMock(return_value=create_valid_image_bytes())

        mock_r2 = MagicMock()
        mock_r2.upload_file = AsyncMock(return_value="test.jpg")

        mock_ctx = MagicMock()
        mock_ctx.deps = {"fal_service": mock_fal, "r2_service": mock_r2}

        result = await generate_and_save_image(
            cast(RunContext[dict], mock_ctx),
            "a cat",
            model="fal-ai/flux/dev"
        )

        assert "fal-ai/flux/dev" in result
        mock_fal.generate_image.assert_called_once_with("a cat", model="fal-ai/flux/dev")

    @pytest.mark.asyncio
    async def test_generate_and_save_image_with_model_hint(self):
        mock_fal = MagicMock(spec=FalService)
        mock_fal.generate_image = AsyncMock(return_value=create_valid_image_bytes())
        mock_fal.search_models.return_value = [
            {"id": "fal-ai/nano-banana-pro", "name": "Nano Banana", "description": "Creative"}
        ]

        mock_r2 = MagicMock()
        mock_r2.upload_file = AsyncMock(return_value="test.jpg")

        mock_ctx = MagicMock()
        mock_ctx.deps = {"fal_service": mock_fal, "r2_service": mock_r2}

        result = await generate_and_save_image(
            cast(RunContext[dict], mock_ctx),
            "a bird",
            model_hint="banana"
        )

        assert "fal-ai/nano-banana-pro" in result
        mock_fal.search_models.assert_called_once_with("banana", limit=1)
        mock_fal.generate_image.assert_called_once_with("a bird", model="fal-ai/nano-banana-pro")

    @pytest.mark.asyncio
    async def test_generate_and_save_image_model_hint_no_match(self):
        mock_fal = MagicMock(spec=FalService)
        mock_fal.generate_image = AsyncMock(return_value=create_valid_image_bytes())
        mock_fal.search_models.return_value = []

        mock_r2 = MagicMock()
        mock_r2.upload_file = AsyncMock(return_value="test.jpg")

        mock_ctx = MagicMock()
        mock_ctx.deps = {"fal_service": mock_fal, "r2_service": mock_r2}

        result = await generate_and_save_image(
            cast(RunContext[dict], mock_ctx),
            "a dog",
            model_hint="nonexistent"
        )

        assert "fal-ai/fast-sdxl" in result
        mock_fal.generate_image.assert_called_once_with("a dog")

    @pytest.mark.asyncio
    async def test_generate_and_save_image_uncompressed(self):
        mock_fal = MagicMock(spec=FalService)
        mock_fal.generate_image = AsyncMock(return_value=create_valid_image_bytes())

        mock_r2 = MagicMock()
        mock_r2.upload_file = AsyncMock(return_value="test.jpg")

        mock_ctx = MagicMock()
        mock_ctx.deps = {"fal_service": mock_fal, "r2_service": mock_r2}

        result = await generate_and_save_image(
            cast(RunContext[dict], mock_ctx),
            "high quality image",
            uncompressed=True
        )

        assert result.endswith(".jpg|fal-ai/fast-sdxl")
        mock_r2.upload_file.assert_called_once()
        
        call_args = mock_r2.upload_file.call_args
        uploaded_data = call_args[0][0]
        assert len(uploaded_data) > 0

    @pytest.mark.asyncio
    async def test_generate_and_save_image_rgba_conversion(self):
        img = Image.new('RGBA', (10, 10), color=(255, 0, 0, 128))
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        rgba_image_bytes = img_byte_arr.getvalue()

        mock_fal = MagicMock(spec=FalService)
        mock_fal.generate_image = AsyncMock(return_value=rgba_image_bytes)

        mock_r2 = MagicMock()
        mock_r2.upload_file = AsyncMock(return_value="test.jpg")

        mock_ctx = MagicMock()
        mock_ctx.deps = {"fal_service": mock_fal, "r2_service": mock_r2}

        result = await generate_and_save_image(
            cast(RunContext[dict], mock_ctx),
            "transparent image"
        )

        assert ".jpg" in result
        mock_r2.upload_file.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_and_save_image_explicit_model_overrides_hint(self):
        mock_fal = MagicMock(spec=FalService)
        mock_fal.generate_image = AsyncMock(return_value=create_valid_image_bytes())
        mock_fal.search_models.return_value = [
            {"id": "fal-ai/nano-banana-pro", "name": "Nano Banana", "description": "Creative"}
        ]

        mock_r2 = MagicMock()
        mock_r2.upload_file = AsyncMock(return_value="test.jpg")

        mock_ctx = MagicMock()
        mock_ctx.deps = {"fal_service": mock_fal, "r2_service": mock_r2}

        result = await generate_and_save_image(
            cast(RunContext[dict], mock_ctx),
            "a car",
            model="fal-ai/recraft/v3",
            model_hint="banana"
        )

        assert "fal-ai/recraft/v3" in result
        mock_fal.search_models.assert_not_called()
        mock_fal.generate_image.assert_called_once_with("a car", model="fal-ai/recraft/v3")
