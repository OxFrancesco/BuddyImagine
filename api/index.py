import os
import logging
import sys
from fastapi import FastAPI, Request, Response
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage

# Add the project root to sys.path so imports work
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from imagine.bot import get_bot, get_dispatcher
from imagine.handlers import router

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

# Initialize bot and dispatcher
# Note: In a serverless environment, these might be re-initialized frequently.
# That's usually fine for aiogram as long as we don't do heavy setup in global scope.
try:
    bot = get_bot()
    dp = get_dispatcher()
    dp.include_router(router)
except Exception as e:
    logger.error(f"Failed to initialize bot/dispatcher: {e}")
    bot = None
    dp = None

@app.get("/")
async def root():
    return {"status": "ok", "service": "BuddyImagine Bot"}

@app.post("/api/webhook")
async def webhook_handler(request: Request):
    """
    Handle incoming Telegram updates via Webhook.
    """
    if not bot or not dp:
        return Response(content="Bot not initialized", status_code=500)

    try:
        # Get the JSON body from the request
        payload = await request.json()
        
        # Convert raw JSON to an aiogram Update object
        update = types.Update(**payload)
        
        # Feed the update to the dispatcher
        await dp.feed_update(bot=bot, update=update)
        
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        # Return 200 even on error to prevent Telegram from retrying endlessly
        return {"status": "error", "message": str(e)}
