import os
import aiohttp
import logging
import base64

logger = logging.getLogger(__name__)

class FalService:
    def __init__(self):
        self.fal_key = os.getenv("FAL_KEY")
        # self.cf_account_id = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        # self.cf_gateway_id = os.getenv("CLOUDFLARE_GATEWAY_ID")
        
        if not self.fal_key:
            logger.warning("FAL credentials missing. FAL service may not work.")

        # Direct FAL API URL
        self.base_url = "https://fal.run"

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
