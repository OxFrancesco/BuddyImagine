import os
import requests
from dotenv import load_dotenv

load_dotenv()

def check_pricing():
    fal_key = os.getenv("FAL_KEY")
    if not fal_key:
        print("FAL_KEY not set")
        return

    headers = {
        "Authorization": f"Key {fal_key}",
        "Content-Type": "application/json"
    }

    # Try with query param
    url = "https://api.fal.ai/v1/models/pricing?model=fal-ai/fast-sdxl"
    print(f"Checking {url}...")
    try:
        response = requests.get(url, headers=headers)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_pricing()
