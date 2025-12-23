import os
import uuid
import io
from typing import Any, TYPE_CHECKING
from PIL import Image
from imagine.services.fal import FalService
from imagine.services.r2 import R2Service

if TYPE_CHECKING:
    from pydantic_ai import CallContext as RunContext

# Lazy agent initialization to avoid import errors when OPENROUTER_API_KEY is not set
_agent: Any = None


# Standalone tool functions for testing and direct use
async def discover_fal_models(
    ctx: "RunContext[dict]",
    query: str = "",
    model_type: str | None = None
) -> str:
    """
    Discover available FAL AI models for image/video generation.
    ALWAYS call this tool first when the user mentions a model name or keyword.
    
    Args:
        ctx: The run context containing dependencies.
        query: Search term (e.g., 'flux', 'nano banana', 'fast', 'realistic', 'anime').
        model_type: Optional filter - 'text-to-image', 'image-to-image', or 'video'.
    
    Returns:
        List of matching models with IDs, names, descriptions, and estimated costs.
        Use the exact model ID in generate_and_save_image.
    """
    fal_service: FalService = ctx.deps['fal_service']
    matches = fal_service.search_models(query, limit=5, model_type=model_type)
    
    if not matches:
        all_names = ", ".join([m['name'] for m in fal_service.KNOWN_MODELS[:5]])
        return f"No models found matching '{query}'. Available models include: {all_names}"
    
    result = f"Found {len(matches)} model(s) matching '{query}':\n"
    for m in matches:
        cost = fal_service.estimate_cost(m['id'])
        credits = (cost / 0.10) * 1.15
        result += f"- {m['name']}: ID={m['id']} | Type={m.get('type', 'unknown')} | Cost=~{credits:.2f} credits | {m['description']}\n"
    result += "\nUse the exact ID value in generate_and_save_image(model='...')"
    return result


async def search_available_models(ctx: "RunContext[dict]", query: str = "") -> str:
    """
    Search available image generation models by name or keyword.
    (Alias for discover_fal_models - prefer using discover_fal_models directly)
    
    Args:
        ctx: The run context containing dependencies.
        query: Search query (model name, keyword, or partial match).
    """
    fal_service: FalService = ctx.deps['fal_service']
    matches = fal_service.search_models(query, limit=5)
    
    if not matches:
        all_names = ", ".join([m['name'] for m in fal_service.KNOWN_MODELS[:5]])
        return f"No models found matching '{query}'. Available models include: {all_names}"
    
    result = f"Found {len(matches)} model(s) matching '{query}':\n"
    for m in matches:
        result += f"- {m['name']}: {m['id']} ({m['description']})\n"
    return result


async def ask_user_clarification(ctx: "RunContext[dict]", question: str, options: list[str] | None = None) -> str:
    """
    Ask the user a clarifying question when you need more information.
    Use when multiple models match or the request is ambiguous.
    
    Args:
        ctx: The run context containing dependencies.
        question: The question to ask the user.
        options: Optional list of choices to present (e.g., model IDs).
    """
    if options:
        return f"CLARIFICATION_NEEDED|{question}|{','.join(options)}"
    return f"CLARIFICATION_NEEDED|{question}|"


async def generate_and_save_image(
    ctx: "RunContext[dict]",
    prompt: str,
    model: str | None = None,
    model_hint: str | None = None,
    uncompressed: bool = False
) -> str:
    """
    Generates an image based on the prompt and uploads it to cloud storage.
    
    Args:
        ctx: The run context containing dependencies.
        prompt: The description of the image to generate.
        model: The exact model ID if known (e.g., 'fal-ai/flux/dev').
        model_hint: A model name/keyword to search for (e.g., 'nano banana', 'flux', 'recraft').
                   If provided, will fuzzy-search and use the best matching model.
        uncompressed: If True, saves the image with higher quality (costs more). Default is False (compressed).
        
    Returns:
        The filename and model used, separated by |
    """
    fal_service: FalService = ctx.deps['fal_service']
    r2_service: R2Service = ctx.deps['r2_service']
    
    # Resolve model from hint if provided
    resolved_model = model
    if model_hint and not model:
        matches = fal_service.search_models(model_hint, limit=1)
        if matches:
            resolved_model = matches[0]['id']
    
    # Generate
    if resolved_model:
        image_data = await fal_service.generate_image(prompt, model=resolved_model)
    else:
        image_data = await fal_service.generate_image(prompt)
    
    # Compression Logic
    img: Image.Image = Image.open(io.BytesIO(image_data))
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
    
    # Return filename and model used for credit calculation
    model_used = resolved_model or "fal-ai/fast-sdxl"
    return f"{filename}|{model_used}"


def get_agent() -> Any:
    """Get or create the agent instance lazily.
    
    This function creates the agent on first call to avoid import-time errors
    when OPENROUTER_API_KEY is not set in the environment.
    """
    global _agent
    if _agent is None:
        from pydantic_ai import Agent
        
        _agent = Agent(
            'openrouter:anthropic/claude-haiku-4.5',
            deps_type=dict,
            system_prompt=(
                "You are an image generation assistant. Your job is to help users create images.\n\n"
                "WORKFLOW:\n"
                "1. If the user mentions ANY model name or wants to choose a model, ALWAYS call discover_fal_models first\n"
                "2. After discovering models, select the most appropriate one based on the user's request\n"
                "3. Call generate_and_save_image with the exact model ID from discovery\n\n"
                "MODEL KEYWORDS TO WATCH FOR:\n"
                "flux, nano banana, banana, recraft, ideogram, sdxl, fooocus, aura, hunyuan, kling, luma, minimax, redux, schnell\n\n"
                "EXAMPLES:\n"
                "- 'a cat with flux' -> discover_fal_models(query='flux') -> generate_and_save_image(prompt='a cat', model='fal-ai/flux/dev')\n"
                "- 'bird with nano banana' -> discover_fal_models(query='nano banana') -> generate_and_save_image(prompt='a bird', model='fal-ai/nano-banana-pro')\n"
                "- 'just a dog' -> generate_and_save_image(prompt='a dog') (use default model)\n"
                "- 'anime style cat with fast model' -> discover_fal_models(query='fast') -> pick fastest model\n\n"
                "QUALITY SETTINGS:\n"
                "- 'uncompressed', 'high quality', 'original' -> set uncompressed=True\n\n"
                "Return ONLY the raw result from generate_and_save_image (filename|model_id format)."
            ),
        )
        
        # Register the standalone tool functions with the agent
        # Using the module-level functions for consistency with tests
        _agent.tool(discover_fal_models)
        _agent.tool(search_available_models)
        _agent.tool(ask_user_clarification)
        _agent.tool(generate_and_save_image)

    return _agent


# Backward compatibility: expose agent as a module-level variable
# This will raise an error only when actually accessed if OPENROUTER_API_KEY is not set
class _LazyAgent:
    """Lazy proxy for the agent that only initializes when accessed."""
    
    def __getattr__(self, name: str) -> Any:
        return getattr(get_agent(), name)
    
    async def run(self, *args: Any, **kwargs: Any) -> Any:
        return await get_agent().run(*args, **kwargs)


agent = _LazyAgent()
