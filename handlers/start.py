from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User
from keyboards.main_kb import get_main_keyboard

router = Router()


async def get_or_create_user(session: AsyncSession, telegram_id: int) -> User:
    """Получить или создать пользователя"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(telegram_id=telegram_id, daily_goal=2000)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    return user


@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession, state: FSMContext):
    """Обработчик команды /start"""
    await state.clear()
    await get_or_create_user(session, message.from_user.id)

    welcome_text = (
        "👋 Привет! Я бот для подсчёта калорий.\n\n"
        "📝 Что я умею:\n"
        "• Считать калории съеденных продуктов\n"
        "• Вести дневную статистику\n"
        "• Отслеживать вашу норму калорий\n\n"
        "💡 Используй кнопки ниже для управления"
    )

    await message.answer(welcome_text, reply_markup=get_main_keyboard())


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обработчик команды /help"""
    help_text = (
        "📋 Как пользоваться ботом:\n\n"
        "➕ Добавить продукт - добавить съеденный продукт\n"
        "📊 Статистика дня - все продукты за сегодня\n"
        "🎯 Моя норма - установить дневную норму калорий\n"
        "📈 Общая статистика - статистика за всё время\n"
        "🗑️ Удалить продукт - удалить последний продукт\n"
        "❌ Очистить день - удалить все продукты за сегодня\n\n"
        "💡 Используйте кнопки для удобной работы!"
    )

    await message.answer(help_text, reply_markup=get_main_keyboard())