import os
import aiohttp
import asyncio
import logging
import base64
from dataclasses import dataclass, field
from time import time
from typing import Optional
from rapidfuzz import process, fuzz

logger = logging.getLogger(__name__)


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5  # Number of failures before opening circuit
    reset_timeout: float = 60.0  # Seconds before trying again after circuit opens
    half_open_max_calls: int = 1  # Max calls allowed in half-open state


@dataclass
class CircuitBreaker:
    """Simple circuit breaker implementation."""
    config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    _failure_count: int = field(default=0, init=False)
    _last_failure_time: float = field(default=0.0, init=False)
    _state: str = field(default="closed", init=False)  # closed, open, half-open
    _half_open_calls: int = field(default=0, init=False)
    
    def can_execute(self) -> bool:
        """Check if request can proceed."""
        if self._state == "closed":
            return True
        
        if self._state == "open":
            # Check if reset timeout has passed
            if time() - self._last_failure_time >= self.config.reset_timeout:
                self._state = "half-open"
                self._half_open_calls = 0
                logger.info("Circuit breaker entering half-open state")
                return True
            return False
        
        # Half-open state
        if self._half_open_calls < self.config.half_open_max_calls:
            return True
        return False
    
    def record_success(self) -> None:
        """Record a successful call."""
        if self._state == "half-open":
            self._state = "closed"
            self._failure_count = 0
            logger.info("Circuit breaker closed after successful call")
        elif self._state == "closed":
            self._failure_count = 0
    
    def record_failure(self) -> None:
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time()
        
        if self._state == "half-open":
            self._state = "open"
            logger.warning("Circuit breaker opened from half-open state")
        elif self._failure_count >= self.config.failure_threshold:
            self._state = "open"
            logger.warning(f"Circuit breaker opened after {self._failure_count} failures")
        
        if self._state == "half-open":
            self._half_open_calls += 1
    
    def is_open(self) -> bool:
        """Check if circuit is open."""
        return self._state == "open" and not self.can_execute()


@dataclass
class RetryConfig:
    """Configuration for retry logic."""
    max_retries: int = 3
    base_delay: float = 1.0  # Base delay in seconds
    max_delay: float = 30.0  # Maximum delay in seconds
    exponential_base: float = 2.0  # Exponential backoff base

class FalService:
    # Text-to-Image models
    TEXT_TO_IMAGE_MODELS = [
        {"id": "fal-ai/fast-sdxl", "name": "Fast SDXL", "description": "Fast Stable Diffusion XL", "type": "text-to-image"},
        {"id": "fal-ai/flux/dev", "name": "Flux Dev", "description": "Flux.1 Dev - High quality", "type": "text-to-image"},
        {"id": "fal-ai/flux/schnell", "name": "Flux Schnell", "description": "Flux.1 Schnell - Fast", "type": "text-to-image"},
        {"id": "fal-ai/flux-realism", "name": "Flux Realism", "description": "Flux Realism LoRA", "type": "text-to-image"},
        {"id": "fal-ai/recraft/v3", "name": "Recraft V3", "description": "Recraft V3 - Design focused", "type": "text-to-image"},
        {"id": "fal-ai/fooocus", "name": "Fooocus", "description": "Fooocus - Easy to use SDXL", "type": "text-to-image"},
        {"id": "fal-ai/stable-diffusion-v3-medium", "name": "SD3 Medium", "description": "Stable Diffusion 3 Medium", "type": "text-to-image"},
        {"id": "fal-ai/auraflow", "name": "AuraFlow", "description": "AuraFlow", "type": "text-to-image"},
        {"id": "fal-ai/ideogram/v2", "name": "Ideogram V2", "description": "Ideogram V2 - Typography", "type": "text-to-image"},
        {"id": "fal-ai/nano-banana-pro", "name": "Nano Banana", "description": "Nano Banana - Creative & Stylized", "type": "text-to-image"},
    ]
    
    # Image-to-Image models (for /remix)
    IMAGE_TO_IMAGE_MODELS = [
        {"id": "fal-ai/flux/dev/image-to-image", "name": "Flux Dev Img2Img", "description": "Flux.1 Dev Image-to-Image - Best quality", "type": "image-to-image"},
        {"id": "fal-ai/flux/schnell/redux", "name": "Flux Schnell Redux", "description": "Flux.1 Schnell Redux - Fast variations", "type": "image-to-image"},
        {"id": "fal-ai/flux/dev/redux", "name": "Flux Dev Redux", "description": "Flux.1 Dev Redux - High quality variations", "type": "image-to-image"},
        {"id": "fal-ai/flux-pro/v1/redux", "name": "Flux Pro Redux", "description": "Flux Pro Redux - Premium variations", "type": "image-to-image"},
    ]
    
    # Video models
    VIDEO_MODELS = [
        {"id": "fal-ai/hunyuan-video-v1.5/text-to-video", "name": "Hunyuan Video", "description": "Hunyuan Text to Video", "type": "video"},
        {"id": "fal-ai/kling/video", "name": "Kling Video", "description": "Kling Video Generation", "type": "video"},
        {"id": "fal-ai/minimax/video-01/image-to-video", "name": "Minimax Video", "description": "Minimax Image to Video", "type": "video"},
        {"id": "fal-ai/luma-dream-machine", "name": "Luma Dream Machine", "description": "Luma Dream Machine Video", "type": "video"},
    ]
    
    # Combined list for backward compatibility
    KNOWN_MODELS = TEXT_TO_IMAGE_MODELS + IMAGE_TO_IMAGE_MODELS + VIDEO_MODELS

    # Pricing table (approximate cost per megapixel or per generation)
    # Based on research:
    # Flux Dev/Pro: ~$0.025 - $0.05 per MP
    # Fast SDXL: ~$0.001 - $0.005 (often very cheap)
    # Video models: significantly more expensive
    PRICING_TABLE = {
        # Text-to-Image models
        "fal-ai/fast-sdxl": 0.005,
        "fal-ai/flux/dev": 0.03,
        "fal-ai/flux/schnell": 0.01,
        "fal-ai/flux-realism": 0.03,
        "fal-ai/recraft/v3": 0.04,
        "fal-ai/fooocus": 0.01,
        "fal-ai/stable-diffusion-v3-medium": 0.03,
        "fal-ai/auraflow": 0.02,
        "fal-ai/ideogram/v2": 0.05,
        "fal-ai/nano-banana-pro": 0.02,
        # Image-to-Image models
        "fal-ai/flux/dev/image-to-image": 0.04,
        "fal-ai/flux/schnell/redux": 0.015,
        "fal-ai/flux/dev/redux": 0.035,
        "fal-ai/flux-pro/v1/redux": 0.06,
        # Video models (higher cost)
        "fal-ai/hunyuan-video-v1.5/text-to-video": 0.50,
        "fal-ai/kling/video": 0.50,
        "fal-ai/minimax/video-01/image-to-video": 0.50,
        "fal-ai/luma-dream-machine": 0.50,
    }
    
    DEFAULT_COST = 0.05

    def __init__(
        self,
        retry_config: Optional[RetryConfig] = None,
        circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
    ) -> None:
        self.fal_key = os.getenv("FAL_KEY")
        
        if not self.fal_key:
            logger.warning("FAL credentials missing. FAL service may not work.")

        # Direct FAL API URL
        self.base_url = "https://fal.run"
        
        # Retry and circuit breaker configuration
        self.retry_config = retry_config or RetryConfig()
        self.circuit_breaker = CircuitBreaker(
            config=circuit_breaker_config or CircuitBreakerConfig()
        )

    def estimate_cost(self, model: str) -> float:
        """
        Estimates the cost of a generation for a given model.
        """
        return self.PRICING_TABLE.get(model, self.DEFAULT_COST)

    def search_models(
        self, 
        query: str, 
        limit: int = 5, 
        model_type: str | None = None
    ) -> list[dict[str, str]]:
        """
        Fuzzy searches for models based on the query using rapidfuzz.
        
        Args:
            query: The search query.
            limit: Maximum number of results to return.
            model_type: Filter by model type: "text-to-image", "image-to-image", "video", or None for all.
            
        Returns:
            A list of matching model dictionaries, sorted by relevance.
        """
        # Select model list based on type filter
        if model_type == "text-to-image":
            model_list = self.TEXT_TO_IMAGE_MODELS
        elif model_type == "image-to-image":
            model_list = self.IMAGE_TO_IMAGE_MODELS
        elif model_type == "video":
            model_list = self.VIDEO_MODELS
        else:
            model_list = self.KNOWN_MODELS
        
        if not query:
            return model_list[:limit]

        # Prepare choices for fuzzy matching. 
        # We match against a combined string of name + description + id to cover all bases.
        choices = {
            i: f"{model['name']} {model['description']} {model['id']}" 
            for i, model in enumerate(model_list)
        }
        
        # Extract top matches
        # result format: (combined_string, score, index)
        results = process.extract(
            query, 
            choices, 
            scorer=fuzz.WRatio, 
            limit=limit,
            score_cutoff=50  # Minimum score to consider a match
        )
        
        matched_models: list[dict[str, str]] = []
        for match in results:
            # match structure in rapidfuzz 3.x: (match_string, score, key)
            # Since we passed a dict, key is the index 'i'
            index = match[2]
            matched_models.append(model_list[index])
            
        return matched_models

    async def generate_image(self, prompt: str, model: str = "fal-ai/fast-sdxl") -> bytes:
        """
        Generates an image using FAL AI with retry logic and circuit breaker.
        
        Args:
            prompt: The description of the image to generate.
            model: The FAL AI model to use. Defaults to "fal-ai/fast-sdxl".
            
        Returns:
            The image binary data.
            
        Raises:
            Exception: If generation fails after all retries or circuit is open.
        """
        # Check circuit breaker
        if not self.circuit_breaker.can_execute():
            raise Exception("Service temporarily unavailable. Please try again later.")
        
        url = f"{self.base_url}/{model}"
        headers = {
            "Authorization": f"Key {self.fal_key}",
            "Content-Type": "application/json"
        }
        payload: dict[str, str | bool | float | int] = {
            "prompt": prompt,
            "sync_mode": True
        }

        last_exception: Exception | None = None
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                result = await self._execute_generation(url, headers, payload)
                self.circuit_breaker.record_success()
                return result
            except Exception as e:
                last_exception = e
                self.circuit_breaker.record_failure()
                
                # Don't retry on certain errors
                error_str = str(e).lower()
                if "unauthorized" in error_str or "forbidden" in error_str:
                    logger.error(f"Authentication error, not retrying: {e}")
                    raise
                if "invalid" in error_str and "prompt" in error_str:
                    logger.error(f"Invalid prompt, not retrying: {e}")
                    raise
                
                # Check if we should retry
                if attempt < self.retry_config.max_retries:
                    delay = min(
                        self.retry_config.base_delay * (self.retry_config.exponential_base ** attempt),
                        self.retry_config.max_delay
                    )
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.1f}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.retry_config.max_retries + 1} attempts failed")
        
        raise last_exception or Exception("Generation failed")

    async def _execute_generation(
        self, url: str, headers: dict[str, str], payload: dict[str, str | bool | float | int]
    ) -> bytes:
        """Execute a single generation request."""
        logger.info(f"Sending request to FAL: {url}")
        
        timeout = aiohttp.ClientTimeout(total=120)  # 2 minute timeout for generation
        
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 429:
                    raise Exception("FAL API rate limit exceeded")
                
                if response.status == 503:
                    raise Exception("FAL API service unavailable")
                
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"FAL API Error: {response.status}")
                    # Mask sensitive info in logs
                    raise Exception(f"FAL API Error: {response.status}")

                content_type = response.headers.get("Content-Type", "")
                if "image" in content_type:
                    return await response.read()
                
                data = await response.json()
                
                if "images" in data and len(data["images"]) > 0:
                    image_url = data["images"][0]["url"]
                    
                    # Check if it's a Data URI
                    if image_url.startswith("data:image"):
                        try:
                            _, encoded = image_url.split(",", 1)
                            return base64.b64decode(encoded)
                        except Exception as e:
                            raise Exception(f"Failed to decode image data: {e}")
                    
                    # Download the image
                    async with session.get(image_url) as img_response:
                        if img_response.status == 200:
                            return await img_response.read()
                        else:
                            raise Exception(f"Failed to download generated image")
                else:
                    raise Exception("No image in response")

    async def generate_image_to_image(
        self, 
        image_url: str, 
        prompt: str = "",
        model: str = "fal-ai/flux/dev/image-to-image",
        strength: float = 0.85
    ) -> bytes:
        """
        Generates an image variation using FAL AI image-to-image models.
        
        Args:
            image_url: URL of the source image (must be publicly accessible).
            prompt: Optional prompt to guide the generation.
            model: The FAL AI model to use. Defaults to "fal-ai/flux/dev/image-to-image".
            strength: How much to transform the image (0.0 = identical, 1.0 = completely new).
            
        Returns:
            The generated image binary data.
            
        Raises:
            Exception: If generation fails after all retries or circuit is open.
        """
        if not self.circuit_breaker.can_execute():
            raise Exception("Service temporarily unavailable. Please try again later.")
        
        url = f"{self.base_url}/{model}"
        headers = {
            "Authorization": f"Key {self.fal_key}",
            "Content-Type": "application/json"
        }
        
        # Build payload based on model type
        payload: dict[str, str | bool | float | int] = {
            "image_url": image_url,
            "sync_mode": True,
        }
        
        # For redux models (variations without prompt)
        if "redux" in model:
            # Redux models create variations based on the image
            if prompt:
                payload["prompt"] = prompt
        else:
            # For image-to-image models, prompt is required
            payload["prompt"] = prompt or "A high-quality variation of this image"
            payload["strength"] = strength
            payload["num_inference_steps"] = 40
            payload["guidance_scale"] = 3.5

        last_exception: Exception | None = None
        
        for attempt in range(self.retry_config.max_retries + 1):
            try:
                result = await self._execute_generation(url, headers, payload)
                self.circuit_breaker.record_success()
                return result
            except Exception as e:
                last_exception = e
                self.circuit_breaker.record_failure()
                
                error_str = str(e).lower()
                if "unauthorized" in error_str or "forbidden" in error_str:
                    logger.error(f"Authentication error, not retrying: {e}")
                    raise
                if "invalid" in error_str:
                    logger.error(f"Invalid request, not retrying: {e}")
                    raise
                
                if attempt < self.retry_config.max_retries:
                    delay = min(
                        self.retry_config.base_delay * (self.retry_config.exponential_base ** attempt),
                        self.retry_config.max_delay
                    )
                    logger.warning(f"Img2Img attempt {attempt + 1} failed, retrying in {delay:.1f}s: {e}")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.retry_config.max_retries + 1} img2img attempts failed")
        
        raise last_exception or Exception("Image-to-image generation failed")
