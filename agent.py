import os
import uuid
from pydantic_ai import Agent, RunContext
from services.fal import FalService
from services.r2 import R2Service

# Define the agent
# Note: You need to set OPENAI_API_KEY or configure another model provider.
# By default, pydantic-ai uses OpenAI's gpt-4o.
agent = Agent(
    'openai:gpt-4o',
    deps_type=dict,
    system_prompt=(
        "You are a helpful assistant that generates images and saves them to the cloud. "
        "When a user asks to generate an image, you should first generate it using the 'generate_image' tool, "
        "and then upload the result using the 'upload_image' tool. "
        "Always return the final filename of the uploaded image to the user."
    ),
)

@agent.tool
async def generate_image(ctx: RunContext[dict], prompt: str) -> bytes:
    """
    Generates an image based on the prompt.
    
    Args:
        ctx: The run context containing dependencies.
        prompt: The description of the image.
    """
    fal_service: FalService = ctx.deps['fal_service']
    return await fal_service.generate_image(prompt)

@agent.tool
async def upload_image(ctx: RunContext[dict], image_data: bytes, filename: str | None = None) -> str:
    """
    Uploads an image to cloud storage.
    
    Args:
        ctx: The run context containing dependencies.
        image_data: The binary data of the image.
        filename: Optional filename. If not provided, a random one is generated.
    """
    r2_service: R2Service = ctx.deps['r2_service']
    if not filename:
        filename = f"{uuid.uuid4()}.jpg"
    return await r2_service.upload_file(image_data, filename)
