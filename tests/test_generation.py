import asyncio
import os
import logging
from dotenv import load_dotenv
from services.fal import FalService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_fal_generation():
    load_dotenv()
    
    fal_service = FalService()
    prompt = "A cute robot holding a flower"
    
    print(f"🚀 Testing FAL generation with prompt: '{prompt}'")
    
    try:
        # We want to inspect what generate_image returns or where it fails
        # But generate_image returns bytes. If it fails inside, we'll catch it.
        # To debug the response structure, we might need to modify FalService temporarily 
        # or just rely on the logs if we set level to DEBUG.
        
        # However, since I suspect the issue is inside generate_image handling the URL,
        # running this should trigger the same error.
        
        image_bytes = await fal_service.generate_image(prompt)
        
        print(f"✅ Generation successful!")
        print(f"   Output type: {type(image_bytes)}")
        print(f"   Output size: {len(image_bytes)} bytes")
        
        # Save to file to verify
        with open("test_output.jpg", "wb") as f:
            f.write(image_bytes)
        print("   Saved to test_output.jpg")
        
    except Exception as e:
        print(f"❌ Generation failed: {e}")
        # If it's the data URI error, it will print here.

if __name__ == "__main__":
    asyncio.run(test_fal_generation())
