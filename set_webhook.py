import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from imagine.bot import get_bot

async def set_webhook():
    print("🤖 Telegram Webhook Setup for Vercel")
    print("------------------------------------")
    
    # Get Bot Token
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("❌ Error: TELEGRAM_BOT_TOKEN not found in environment variables.")
        print("Please ensure you have a .env file or set the variable.")
        return

    # Get Vercel URL
    vercel_url = input("Enter your Vercel Project URL (e.g., https://your-project.vercel.app): ").strip()
    if not vercel_url.startswith("https://"):
        if vercel_url.startswith("http://"):
            print("⚠️ Warning: Telegram webhooks require HTTPS. Using http:// but it might fail.")
        else:
            vercel_url = f"https://{vercel_url}"
    
    # Remove trailing slash if present
    if vercel_url.endswith("/"):
        vercel_url = vercel_url[:-1]
        
    webhook_url = f"{vercel_url}/api/webhook"
    print(f"\nSetting webhook to: {webhook_url}")
    
    try:
        bot = get_bot()
        # Drop pending updates to avoid a flood of old messages
        await bot.delete_webhook(drop_pending_updates=True)
        print("✅ Old webhook deleted and pending updates dropped.")
        
        # Set new webhook
        await bot.set_webhook(webhook_url)
        print(f"✅ Webhook successfully set to {webhook_url}")
        
        info = await bot.get_webhook_info()
        print("\nWebhook Info:")
        print(f"URL: {info.url}")
        print(f"Pending updates: {info.pending_update_count}")
        
    except Exception as e:
        print(f"❌ Failed to set webhook: {e}")
    finally:
        if 'bot' in locals() and bot.session:
            await bot.session.close()

if __name__ == "__main__":
    asyncio.run(set_webhook())
