import os
import requests
from dotenv import load_dotenv

load_dotenv()

ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
GATEWAY_ID = os.getenv("CLOUDFLARE_GATEWAY_ID")
# You need a Cloudflare API Token with "AI Gateway: Read" permissions
# If you don't have one in .env, you'll need to provide it.
# We'll try to read it from CLOUDFLARE_API_TOKEN if it exists, 
# otherwise we'll ask the user or fail.
CF_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")

def check_gateway_config():
    if not all([ACCOUNT_ID, GATEWAY_ID]):
        print("❌ Missing CLOUDFLARE_ACCOUNT_ID or CLOUDFLARE_GATEWAY_ID in .env")
        return

    if not CF_API_TOKEN:
        print("⚠️  CLOUDFLARE_API_TOKEN not found in .env.")
        print("   Please create an API Token with 'AI Gateway: Read' permissions at https://dash.cloudflare.com/profile/api-tokens")
        print("   and add it to your .env file as CLOUDFLARE_API_TOKEN=...")
        return

    print(f"🔍 Checking configuration for Gateway '{GATEWAY_ID}' in Account '{ACCOUNT_ID}'...")

    url = f"https://api.cloudflare.com/client/v4/accounts/{ACCOUNT_ID}/ai-gateway/gateways/{GATEWAY_ID}"
    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                gateway = data.get("result", {})
                print("\n✅ Gateway Found!")
                print(f"   Name: {gateway.get('name')}")
                print(f"   ID: {gateway.get('id')}")
                # Check providers/settings if available in the response
                # Note: The API response structure might vary, we'll dump relevant parts.
                print("\n   Configuration Details:")
                # Assuming 'providers' or similar key exists, or we just print the whole thing for inspection
                # The 'universal endpoint' config is often implicit or part of the settings.
                import json
                print(json.dumps(gateway, indent=2))
            else:
                print(f"\n❌ API Request Failed: {data.get('errors')}")
        elif response.status_code == 404:
            print(f"\n❌ Gateway '{GATEWAY_ID}' not found. Please check the ID.")
        elif response.status_code == 401:
             print(f"\n❌ Unauthorized. Please check your CLOUDFLARE_API_TOKEN.")
        else:
            print(f"\n❌ Error {response.status_code}: {response.text}")

    except Exception as e:
        print(f"\n❌ An error occurred: {e}")

if __name__ == "__main__":
    check_gateway_config()
