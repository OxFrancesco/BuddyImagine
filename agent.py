import os
import uuid
import io
from PIL import Image
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
        "When a user asks to generate an image, use the 'generate_and_save_image' tool. "
        "This tool will handle both generation and uploading. "
        "Return ONLY the filename of the uploaded image as your final response, with no other text.\n"
        "If the user specifies a model (e.g., 'flux', 'sdxl', 'recraft', 'ideogram', or a specific model ID), "
        "pass it to the tool as the 'model' argument. "
        "If the user asks for 'uncompressed', 'high quality', or 'original quality' image, set the 'uncompressed' argument to True. "
        "Otherwise, leave 'uncompressed' as False (default). "
        "Common mappings: 'flux' -> 'fal-ai/flux/dev', 'fast' -> 'fal-ai/flux/schnell', 'sdxl' -> 'fal-ai/fast-sdxl'. "
        "If no model is specified, do not set the model argument (it will default to SDXL)."
    ),
)

@agent.tool
async def generate_and_save_image(
    ctx: RunContext[dict],
    prompt: str,
    model: str | None = None,
    uncompressed: bool = False
) -> str:
    """
    Generates an image based on the prompt and uploads it to cloud storage.
    
    Args:
        ctx: The run context containing dependencies.
        prompt: The description of the image.
        model: Optional. The specific model ID to use (e.g., 'fal-ai/flux/dev').
        uncompressed: If True, saves the image with higher quality (costs more). Default is False (compressed).
        
    Returns:
        The filename of the saved image.
    """
    fal_service: FalService = ctx.deps['fal_service']
    r2_service: R2Service = ctx.deps['r2_service']
    
    # Generate
    if model:
        image_data = await fal_service.generate_image(prompt, model=model)
    else:
        image_data = await fal_service.generate_image(prompt)
    
    # Compression Logic
    img = Image.open(io.BytesIO(image_data))
    output_buffer = io.BytesIO()

    # Always convert to RGB to ensure compatibility with JPEG
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    if uncompressed:
        # High quality (paid)
        img.save(output_buffer, format="JPEG", quality=95)
    else:
        # Standard compression (default)
        img.save(output_buffer, format="JPEG", quality=60, optimize=True)

    final_image_data = output_buffer.getvalue()

    # Upload
    filename = f"{uuid.uuid4()}.jpg"
    await r2_service.upload_file(final_image_data, filename)
    
    return filename
