import pytest
from agent import agent

@pytest.mark.asyncio
async def test_agent_flow(mock_fal_service, mock_r2_service):
    deps = {
        'fal_service': mock_fal_service,
        'r2_service': mock_r2_service
    }
    
    # We can't easily mock the LLM response without an API key or a complex mock of the model.
    # However, we can test the tools directly or use pydantic-ai's testing utilities if available.
    # For this basic suite, let's verify the tools are registered and callable via the agent structure
    # by invoking them as if the agent did.
    
    # Test generate_image tool
    # Note: In pydantic-ai < 0.0.14 (or similar early versions), accessing tools might differ.
    # Assuming we can access the decorated functions directly or via the agent instance.
    # The decorated functions are wrappers.
    
    # Let's try running the agent with a mock model if possible, or just test the tool logic.
    # Since we don't have a mock LLM setup easily without external calls, 
    # we will verify the tool functions themselves which contain the logic bridging the agent and services.
    
    from agent import generate_image, upload_image
    from pydantic_ai import RunContext
    
    # Create a fake context
    ctx = RunContext(deps=deps, retry=0, tool_name='test', model=None, usage=None, prompt=None)
    
    # Test generate
    img_data = await generate_image(ctx, "test prompt")
    assert img_data == b"fake_image_data"
    mock_fal_service.generate_image.assert_called_with("test prompt")
    
    # Test upload
    filename = await upload_image(ctx, b"fake_data")
    assert filename == "test_image.jpg"
    mock_r2_service.upload_file.assert_called()
