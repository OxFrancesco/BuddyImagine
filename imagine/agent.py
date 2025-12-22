import os
import uuid
import io
from typing import Any
from PIL import Image
from imagine.services.fal import FalService
from imagine.services.r2 import R2Service

# Lazy agent initialization to avoid import errors when OPENROUTER_API_KEY is not set
_agent: Any = None


def get_agent() -> Any:
    """Get or create the agent instance lazily.
    
    This function creates the agent on first call to avoid import-time errors
    when OPENROUTER_API_KEY is not set in the environment.
    """
    global _agent
    if _agent is None:
        from pydantic_ai import Agent, RunContext
        
        _agent = Agent(
            'openrouter:anthropic/claude-haiku-4.5',
            deps_type=dict,
            system_prompt=(
                "You are an image generation assistant. Call generate_and_save_image to create images.\n\n"
                "IMPORTANT: If the user mentions a model name (flux, nano banana, recraft, ideogram, sdxl, etc.), "
                "pass it to the 'model_hint' parameter and the tool will find the correct model.\n"
                "Examples:\n"
                "- 'a cat with flux' -> generate_and_save_image(prompt='a cat', model_hint='flux')\n"
                "- 'bird with nano banana' -> generate_and_save_image(prompt='a bird', model_hint='nano banana')\n"
                "- 'just a dog' -> generate_and_save_image(prompt='a dog') (no model_hint needed)\n\n"
                "For quality: 'uncompressed', 'high quality', 'original' -> set uncompressed=True\n"
                "Return ONLY the raw result from generate_and_save_image."
            ),
        )
        
        # Register tools
        @_agent.tool
        async def search_available_models(ctx: RunContext[dict], query: str = "") -> str:
            """
            Search available image generation models by name or keyword.
            Returns a list of matching models with their IDs and descriptions.
            Use this when the user mentions a model name or you need to find the right model.
            
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

        @_agent.tool
        async def ask_user_clarification(ctx: RunContext[dict], question: str, options: list[str] | None = None) -> str:
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

        @_agent.tool
        async def generate_and_save_image(
            ctx: RunContext[dict],
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
