import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

def get_bot() -> Bot:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment variables")
    
    return Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

def get_dispatcher() -> Dispatcher:
    return Dispatcher()
