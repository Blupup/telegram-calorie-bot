import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from database.db import init_db, async_session_maker
from services.init_data import load_products
from handlers import start, add_meal, stats

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def on_startup():
    """Действия при запуске бота"""
    logger.info("🚀 Инициализация базы данных...")
    await init_db()

    logger.info("📦 Загрузка продуктов...")
    async with async_session_maker() as session:
        await load_products(session)

    logger.info("✅ Бот запущен!")


async def on_shutdown():
    """Действия при остановке бота"""
    logger.info("👋 Бот остановлен")


async def main():
    """Главная функция запуска бота"""
    # Создаём бот и диспетчер
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Регистрируем роутеры
    dp.include_router(start.router)
    dp.include_router(add_meal.router)
    dp.include_router(stats.router)

    # Middleware для автоматической передачи сессии в хендлеры
    @dp.update.middleware()
    async def db_session_middleware(handler, event, data):
        async with async_session_maker() as session:
            data["session"] = session
            return await handler(event, data)

    # Запуск
    await on_startup()

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await on_shutdown()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️ Бот остановлен пользователем")