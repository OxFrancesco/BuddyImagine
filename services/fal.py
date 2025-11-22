import os
import aiohttp
import logging
import base64
from typing import List, Dict
from rapidfuzz import process, fuzz

logger = logging.getLogger(__name__)

class FalService:
    KNOWN_MODELS = [
        {"id": "fal-ai/fast-sdxl", "name": "Fast SDXL", "description": "Fast Stable Diffusion XL"},
        {"id": "fal-ai/flux/dev", "name": "Flux Dev", "description": "Flux.1 Dev - High quality"},
        {"id": "fal-ai/flux/schnell", "name": "Flux Schnell", "description": "Flux.1 Schnell - Fast"},
        {"id": "fal-ai/flux-realism", "name": "Flux Realism", "description": "Flux Realism LoRA"},
        {"id": "fal-ai/recraft/v3", "name": "Recraft V3", "description": "Recraft V3 - Design focused"},
        {"id": "fal-ai/fooocus", "name": "Fooocus", "description": "Fooocus - Easy to use SDXL"},
        {"id": "fal-ai/stable-diffusion-v3-medium", "name": "SD3 Medium", "description": "Stable Diffusion 3 Medium"},
        {"id": "fal-ai/auraflow", "name": "AuraFlow", "description": "AuraFlow"},
        {"id": "fal-ai/ideogram/v2", "name": "Ideogram V2", "description": "Ideogram V2 - Typography"},
        {"id": "fal-ai/nanobanana-pro", "name": "Nano Banana", "description": "Nano Banana - Creative & Stylized"},
        {"id": "fal-ai/hunyuan-video-v1.5/text-to-video", "name": "Hunyuan Video", "description": "Hunyuan Text to Video"},
        {"id": "fal-ai/kling/video", "name": "Kling Video", "description": "Kling Video Generation"},
        {"id": "fal-ai/minimax/video-01/image-to-video", "name": "Minimax Video", "description": "Minimax Image to Video"},
        {"id": "fal-ai/luma-dream-machine", "name": "Luma Dream Machine", "description": "Luma Dream Machine Video"},
    ]

    # Pricing table (approximate cost per megapixel or per generation)
    # Based on research:
    # Flux Dev/Pro: ~$0.025 - $0.05 per MP
    # Fast SDXL: ~$0.001 - $0.005 (often very cheap)
    # Video models: significantly more expensive
    PRICING_TABLE = {
        "fal-ai/fast-sdxl": 0.005, # Estimate
        "fal-ai/flux/dev": 0.03,
        "fal-ai/flux/schnell": 0.01,
        "fal-ai/flux-realism": 0.03,
        "fal-ai/recraft/v3": 0.04,
        "fal-ai/fooocus": 0.01,
        "fal-ai/stable-diffusion-v3-medium": 0.03,
        "fal-ai/auraflow": 0.02,
        "fal-ai/ideogram/v2": 0.05,
        "fal-ai/nanobanana-pro": 0.02,
        # Video models (higher cost)
        "fal-ai/hunyuan-video-v1.5/text-to-video": 0.50,
        "fal-ai/kling/video": 0.50,
        "fal-ai/minimax/video-01/image-to-video": 0.50,
        "fal-ai/luma-dream-machine": 0.50,
    }
    
    DEFAULT_COST = 0.05

    def __init__(self):
        self.fal_key = os.getenv("FAL_KEY")
        # self.cf_account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        # self.cf_gateway_id = os.getenv("CLOUDFLARE_GATEWAY_ID")
        
        if not self.fal_key:
            logger.warning("FAL credentials missing. FAL service may not work.")

        # Direct FAL API URL
        self.base_url = "https://fal.run"

    def estimate_cost(self, model: str) -> float:
        """
        Estimates the cost of a generation for a given model.
        """
        return self.PRICING_TABLE.get(model, self.DEFAULT_COST)

    def search_models(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        """
        Fuzzy searches for models based on the query using rapidfuzz.
        
        Args:
            query: The search query.
            limit: Maximum number of results to return.
            
        Returns:
            A list of matching model dictionaries, sorted by relevance.
        """
        if not query:
            return self.KNOWN_MODELS[:limit]

        # Prepare choices for fuzzy matching. 
        # We match against a combined string of name + description + id to cover all bases.
        choices = {
            i: f"{model['name']} {model['description']} {model['id']}" 
            for i, model in enumerate(self.KNOWN_MODELS)
        }
        
        # Extract top matches
        # result format: (combined_string, score, index)
        results = process.extract(
            query, 
            choices, 
            scorer=fuzz.WRatio, 
            limit=limit,
            score_cutoff=50 # Minimum score to consider a match
        )
        
        matched_models = []
        for match in results:
            # match structure in rapidfuzz 3.x: (match_string, score, key)
            # Since we passed a dict, key is the index 'i'
            index = match[2]
            matched_models.append(self.KNOWN_MODELS[index])
            
        return matched_models

    async def generate_image(self, prompt: str, model: str = "fal-ai/fast-sdxl") -> bytes:
        """
        Generates an image using FAL AI directly.
        
        Args:
            prompt: The description of the image to generate.
            model: The FAL AI model to use. Defaults to "fal-ai/fast-sdxl".
            
        Returns:
            The image binary data.
        """
        url = f"{self.base_url}/{model}"
        headers = {
            "Authorization": f"Key {self.fal_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "prompt": prompt,
            "sync_mode": True # Request synchronous generation for simplicity
        }

        logger.info(f"Sending request to FAL via Cloudflare Gateway: {url}")
        # logger.debug(f"Payload: {payload}") # Uncomment if you want to see the prompt in logs

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"FAL API Error: {response.status}")
                        logger.error(f"Response Body: {error_text}")
                        logger.error(f"Request URL: {url}")
                        # Check if headers are correct (masking key)
                        masked_headers = headers.copy()
                        masked_headers["Authorization"] = "Key *****"
                        logger.error(f"Request Headers: {masked_headers}")
                        
                        raise Exception(f"FAL API Error: {response.status} - {error_text}")

                    content_type = response.headers.get("Content-Type", "")
                    if "image" in content_type:
                        return await response.read()
                    
                    data = await response.json()
                    
                    # FAL usually returns a JSON with an 'images' list containing objects with 'url'
                    # Example: {'images': [{'url': '...', 'width': 1024, 'height': 1024, ...}]}
                    if 'images' in data and len(data['images']) > 0:
                        image_url = data['images'][0]['url']
                        
                        # Check if it's a Data URI
                        if image_url.startswith("data:image"):
                            # Format: data:image/jpeg;base64,/9j/4AAQSkZJRg...
                            try:
                                header, encoded = image_url.split(",", 1)
                                return base64.b64decode(encoded)
                            except Exception as e:
                                raise Exception(f"Failed to decode Data URI: {e}")
                        
                        # Otherwise, download the image content
                        async with session.get(image_url) as img_response:
                            if img_response.status == 200:
                                return await img_response.read()
                            else:
                                raise Exception(f"Failed to download generated image: {img_response.status}")
                    else:
                         # Some endpoints might return the image directly in a 'image' field as base64?
                         # Or maybe we just handled the direct binary case above.
                         raise Exception(f"No image URL found in FAL response: {data}")

            except Exception as e:
                logger.error(f"Error generating image: {e}")
                raise
