import os
import asyncio
import aiohttp
from dotenv import load_dotenv

load_dotenv()

async def check_model(model_id):
    url = f"https://fal.run/{model_id}"
    headers = {
        "Authorization": f"Key {os.getenv('FAL_KEY')}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": "test",
        "sync_mode": True
    }
    
    print(f"Checking {model_id}...")
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status == 200:
                print(f"✅ {model_id} EXISTS")
            else:
                print(f"❌ {model_id} FAILED: {response.status}")
                print(await response.text())

async def main():
    models_to_check = [
        "fal-ai/nanobanana-pro", # Current (failed)
        "fal-ai/nano-banana-pro", # Hyphenated
        "fal-ai/nano-banana", # Base
        "fal-ai/gempix2", # New name?
    ]
    
    for model in models_to_check:
        await check_model(model)

if __name__ == "__main__":
    asyncio.run(main())
