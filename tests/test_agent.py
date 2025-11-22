import pytest
from unittest.mock import AsyncMock, MagicMock
from typing import cast, Any
from pydantic_ai import RunContext
from agent import generate_and_save_image

@pytest.mark.asyncio
async def test_generate_and_save_image(mock_fal_service: AsyncMock, mock_r2_service: AsyncMock) -> None:
    deps = {
        'fal_service': mock_fal_service,
        'r2_service': mock_r2_service
    }
    
    # Create a mock context that mimics RunContext
    # We use MagicMock for runtime behavior and cast for static type checking
    mock_ctx = MagicMock()
    mock_ctx.deps = deps
    
    # Mock the services
    mock_fal_service.generate_image.return_value = b"fake_image_data"
    
    # Run the tool function
    # We cast mock_ctx to RunContext[dict] to satisfy mypy
    filename = await generate_and_save_image(cast(RunContext[dict], mock_ctx), "test prompt")
    
    # Assertions
    assert filename.endswith(".jpg")
    mock_fal_service.generate_image.assert_called_with("test prompt")
    mock_r2_service.upload_file.assert_called()
    
    # Check that upload_file was called with the correct data
    call_args = mock_r2_service.upload_file.call_args
    assert call_args is not None
    args, _ = call_args
    uploaded_data, uploaded_filename = args
    assert uploaded_data == b"fake_image_data"
    assert uploaded_filename == filename