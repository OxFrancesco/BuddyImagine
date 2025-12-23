import asyncio
import logging
import sys
from dotenv import load_dotenv

# Load environment variables before importing other modules
load_dotenv()

from imagine.bot import get_bot, get_dispatcher
from imagine.handlers import router
from imagine.handlers_payments import router as payments_router

from aiogram.types import BotCommand, BotCommandScopeDefault

async def main():
    # Configure logging
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    
    bot = get_bot()
    dp = get_dispatcher()
    
    # Register routers
    dp.include_router(router)
    dp.include_router(payments_router)
    
    # Set bot commands for Telegram UI
    commands = [
        BotCommand(command="/start", description="Start the bot"),
        BotCommand(command="/imagine", description="Generate an image from text"),
        BotCommand(command="/remix", description="Transform your last image"),
        BotCommand(command="/models", description="List or search FAL models"),
        BotCommand(command="/setmodel", description="Set default model"),
        BotCommand(command="/credits", description="View credit balance"),
        BotCommand(command="/buy", description="Buy credits"),
        BotCommand(command="/settings", description="View/update settings"),
        BotCommand(command="/help", description="Show help message"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())
    
    logging.info("Starting bot polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
