import asyncio
import logging
import sys
from dotenv import load_dotenv

# Load environment variables before importing other modules
load_dotenv()

from bot import get_bot, get_dispatcher
from handlers import router

async def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    bot = get_bot()
    dp = get_dispatcher()
    
    # Register routers
    dp.include_router(router)
    
    logging.info("Starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
