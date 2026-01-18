from datetime import date
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, Meal
from states.user_states import SetGoalStates
from keyboards.main_kb import get_main_keyboard, get_cancel_keyboard

router = Router()


@router.message(F.text == "📊 Статистика дня")
async def show_day_stats(message: Message, session: AsyncSession):
    """Показать подробную статистику за сегодня"""
    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("❌ Пользователь не найден. Нажмите /start", reply_markup=get_main_keyboard())
        return

    # Получаем все продукты за сегодня
    meals_result = await session.execute(
        select(Meal).where(
            Meal.user_id == user.id,
            Meal.date == date.today()
        ).order_by(Meal.id)
    )
    meals = meals_result.scalars().all()

    if not meals:
        await message.answer(
            "📭 Сегодня ещё не добавлено ни одного продукта\n\n"
            "Нажмите '➕ Добавить продукт' чтобы начать",
            reply_markup=get_main_keyboard()
        )
        return

    # Формируем подробный список
    lines = ["📅 Статистика за сегодня:\n"]
    total_calories = 0

    for i, meal in enumerate(meals, 1):
        lines.append(
            f"{i}. {meal.product_name.capitalize()}\n"
            f"   ⚖️ {meal.grams}г  |  🔥 {int(meal.calories)} ккал"
        )
        total_calories += meal.calories

    lines.append(f"\n{'─' * 30}")
    lines.append(f"📊 Всего продуктов: {len(meals)}")
    lines.append(f"🔥 Всего калорий: {int(total_calories)} / {user.daily_goal} ккал")

    if total_calories > user.daily_goal:
        lines.append(f"⚠️ Превышение на {int(total_calories - user.daily_goal)} ккал")
    else:
        remaining = user.daily_goal - total_calories
        percentage = (total_calories / user.daily_goal) * 100
        lines.append(f"✅ Осталось: {int(remaining)} ккал ({int(percentage)}%)")

    await message.answer("\n".join(lines), reply_markup=get_main_keyboard())


@router.message(F.text == "🎯 Моя норма")
async def start_set_goal(message: Message, state: FSMContext):
    """Начало установки нормы калорий"""
    await state.set_state(SetGoalStates.waiting_for_goal)
    await message.answer(
        "🎯 Введите вашу дневную норму калорий:\n\n"
        "Например: 2000\n\n"
        "💡 Рекомендуемые нормы:\n"
        "• Женщины: 1800-2200 ккал\n"
        "• Мужчины: 2200-2800 ккал",
        reply_markup=get_cancel_keyboard()
    )


@router.message(SetGoalStates.waiting_for_goal, F.text == "❌ Отмена")
async def cancel_set_goal(message: Message, state: FSMContext):
    """Отмена установки нормы"""
    await state.clear()
    await message.answer("❌ Установка нормы отменена", reply_markup=get_main_keyboard())


@router.message(SetGoalStates.waiting_for_goal)
async def process_goal(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка ввода нормы калорий"""
    if not message.text.isdigit():
        await message.answer(
            "❌ Пожалуйста, введите число (только цифры)\n"
            "Например: 2000",
            reply_markup=get_cancel_keyboard()
        )
        return

    new_goal = int(message.text)

    if new_goal < 500 or new_goal > 10000:
        await message.answer(
            "❌ Норма должна быть от 500 до 10000 ккал\n"
            "Попробуйте ещё раз:",
            reply_markup=get_cancel_keyboard()
        )
        return

    # Обновляем пользователя
    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(telegram_id=message.from_user.id, daily_goal=new_goal)
        session.add(user)
    else:
        user.daily_goal = new_goal

    await session.commit()
    await state.clear()

    await message.answer(
        f"✅ Дневная норма установлена: {new_goal} ккал\n\n"
        f"Теперь вы можете добавлять продукты!",
        reply_markup=get_main_keyboard()
    )


@router.message(F.text == "📈 Общая статистика")
async def show_general_stats(message: Message, session: AsyncSession):
    """Показать общую статистику"""
    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("❌ Пользователь не найден. Нажмите /start", reply_markup=get_main_keyboard())
        return

    # Общее количество дней с записями
    days_result = await session.execute(
        select(func.count(func.distinct(Meal.date))).where(
            Meal.user_id == user.id
        )
    )
    total_days = days_result.scalar() or 0

    # Общее количество записей
    meals_result = await session.execute(
        select(func.count(Meal.id)).where(
            Meal.user_id == user.id
        )
    )
    total_meals = meals_result.scalar() or 0

    # Средние калории на приём пищи
    avg_meal_result = await session.execute(
        select(func.avg(Meal.calories)).where(
            Meal.user_id == user.id
        )
    )
    avg_meal_calories = avg_meal_result.scalar() or 0

    # Калории за сегодня
    today_result = await session.execute(
        select(func.sum(Meal.calories)).where(
            Meal.user_id == user.id,
            Meal.date == date.today()
        )
    )
    today_calories = today_result.scalar() or 0

    # Общая сумма калорий за всё время
    total_calories_result = await session.execute(
        select(func.sum(Meal.calories)).where(
            Meal.user_id == user.id
        )
    )
    total_calories = total_calories_result.scalar() or 0

    # Средние калории в день
    avg_day_calories = total_calories / total_days if total_days > 0 else 0

    stats_text = (
        "📈 Общая статистика:\n\n"
        f"🎯 Дневная норма: {user.daily_goal} ккал\n"
        f"📅 Дней с записями: {total_days}\n"
        f"🍽️ Всего приёмов пищи: {total_meals}\n\n"
        f"📊 Средние показатели:\n"
        f"• На приём пищи: {int(avg_meal_calories)} ккал\n"
        f"• В день: {int(avg_day_calories)} ккал\n\n"
        f"🔥 Всего калорий за всё время: {int(total_calories)} ккал\n\n"
        f"📆 Сегодня: {int(today_calories)} / {user.daily_goal} ккал"
    )

    await message.answer(stats_text, reply_markup=get_main_keyboard())