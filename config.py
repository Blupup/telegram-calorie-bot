import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = "sqlite+aiosqlite:///calorie_bot.db"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env файле")