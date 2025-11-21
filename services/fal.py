import os
import aiohttp
import logging

logger = logging.getLogger(__name__)

class FalService:
    def __init__(self):
        self.fal_key = os.getenv("FAL_KEY")
        self.cf_account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        self.cf_gateway_id = os.getenv("CLOUDFLARE_GATEWAY_ID")
        
        if not all([self.fal_key, self.cf_account_id, self.cf_gateway_id]):
            logger.warning("FAL or Cloudflare credentials missing. FAL service may not work.")

        # Construct the Cloudflare AI Gateway URL for FAL
        # Pattern: https://gateway.ai.cloudflare.com/v1/{account_id}/{gateway_id}/fal
        self.base_url = f"https://gateway.ai.cloudflare.com/v1/{self.cf_account_id}/{self.cf_gateway_id}/fal"

    async def generate_image(self, prompt: str, model: str = "fal-ai/fast-sdxl") -> bytes:
        """
        Generates an image using FAL AI via Cloudflare Gateway.
        
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

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"FAL API Error: {response.status} - {error_text}")
                        raise Exception(f"FAL API Error: {response.status}")

                    data = await response.json()
                    
                    # FAL usually returns a JSON with an 'images' list containing objects with 'url'
                    # Example: {'images': [{'url': '...', 'width': 1024, 'height': 1024, ...}]}
                    if 'images' in data and len(data['images']) > 0:
                        image_url = data['images'][0]['url']
                        
                        # Download the image content
                        async with session.get(image_url) as img_response:
                            if img_response.status == 200:
                                return await img_response.read()
                            else:
                                raise Exception(f"Failed to download generated image: {img_response.status}")
                    else:
                         raise Exception("No image URL found in FAL response")

            except Exception as e:
                logger.error(f"Error generating image: {e}")
                raise
