import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import cast, Any
from pydantic_ai import RunContext
from agent import generate_and_save_image

@pytest.mark.asyncio
async def test_generate_and_save_image_default(mock_fal_service: AsyncMock, mock_r2_service: AsyncMock) -> None:
    deps = {
        'fal_service': mock_fal_service,
        'r2_service': mock_r2_service
    }
    
    mock_ctx = MagicMock()
    mock_ctx.deps = deps
    
    mock_fal_service.generate_image.return_value = b"fake_image_data"
    
    # Test without model arg
    filename = await generate_and_save_image(cast(RunContext[dict], mock_ctx), "test prompt")
    
    assert filename.endswith(".jpg")
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
    
    mock_fal_service.generate_image.return_value = b"fake_image_data"
    
    # Test with model arg
    filename = await generate_and_save_image(cast(RunContext[dict], mock_ctx), "test prompt", model="custom/model")
    
    assert filename.endswith(".jpg")
    mock_fal_service.generate_image.assert_called_with("test prompt", model="custom/model")
    mock_r2_service.upload_file.assert_called()
