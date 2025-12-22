import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import cast, Any
from pydantic_ai import RunContext
from imagine.agent import generate_and_save_image

@pytest.mark.asyncio
async def test_generate_and_save_image_default(mock_fal_service: AsyncMock, mock_r2_service: AsyncMock) -> None:
    deps = {
        'fal_service': mock_fal_service,
        'r2_service': mock_r2_service
    }
    
    mock_ctx = MagicMock()
    mock_ctx.deps = deps
    
    # mock_fal_service is already configured by conftest to return valid image bytes.
    # We remove the explicit override that sets it back to invalid bytes.
    
    # Test without model arg
    result = await generate_and_save_image(cast(RunContext[dict], mock_ctx), "test prompt")
    
    # Result format: "filename.jpg|model_id"
    assert ".jpg|" in result
    assert result.endswith("fal-ai/fast-sdxl")
    # Verify called with only prompt (using default model in service) or explicit default?
    # The tool calls service.generate_image(prompt) if model is None.
    mock_fal_service.generate_image.assert_called_with("test prompt")
    mock_r2_service.upload_file.assert_called()

@pytest.mark.asyncio
async def test_generate_and_save_image_with_model(mock_fal_service: AsyncMock, mock_r2_service: AsyncMock) -> None:
    deps = {
        'fal_service': mock_fal_service,
        'r2_service': mock_r2_service
    }
    
    mock_ctx = MagicMock()
    mock_ctx.deps = deps
    
    # mock_fal_service is already configured by conftest to return valid image bytes.
    
    # Test with model arg
    result = await generate_and_save_image(cast(RunContext[dict], mock_ctx), "test prompt", model="custom/model")
    
    # Result format: "filename.jpg|model_id"
    assert ".jpg|" in result
    assert result.endswith("custom/model")
    mock_fal_service.generate_image.assert_called_with("test prompt", model="custom/model")
    mock_r2_service.upload_file.assert_called()
