from datetime import date
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import User, Meal
from services.product_search import find_product, find_similar_products
from states.user_states import AddProductStates
from keyboards.main_kb import get_main_keyboard, get_cancel_keyboard, get_delete_keyboard

router = Router()


@router.message(F.text == "➕ Добавить продукт")
async def start_add_product(message: Message, state: FSMContext):
    """Начало добавления продукта"""
    await state.set_state(AddProductStates.waiting_for_product)
    await message.answer(
        "📝 Введите название продукта:\n\n"
        "Например: яблоко, куриная грудка, рис",
        reply_markup=get_cancel_keyboard()
    )


@router.message(AddProductStates.waiting_for_product, F.text == "❌ Отмена")
async def cancel_add_product(message: Message, state: FSMContext):
    """Отмена добавления продукта"""
    await state.clear()
    await message.answer("❌ Добавление отменено", reply_markup=get_main_keyboard())


@router.message(AddProductStates.waiting_for_product)
async def process_product_name(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка названия продукта"""
    product_name = message.text.strip().lower()

    # Ищем продукт
    product = await find_product(session, product_name)

    if not product:
        # Продукт не найден, ищем похожие
        similar = await find_similar_products(session, product_name)

        if similar:
            suggestions = "\n".join([f"• {p}" for p in similar[:5]])
            await message.answer(
                f"❌ Продукт '{product_name}' не найден.\n\n"
                f"Похожие продукты:\n{suggestions}\n\n"
                "Попробуйте ещё раз или нажмите Отмена",
                reply_markup=get_cancel_keyboard()
            )
        else:
            await message.answer(
                f"❌ Продукт '{product_name}' не найден в базе.\n\n"
                "Попробуйте другое название или нажмите Отмена",
                reply_markup=get_cancel_keyboard()
            )
        return

    # Сохраняем продукт в состояние
    await state.update_data(product=product)
    await state.set_state(AddProductStates.waiting_for_grams)

    await message.answer(
        f"✅ {product.name.capitalize()}\n"
        f"🔥 {product.kcal_per_100g} ккал на 100г\n\n"
        f"⚖️ Введите количество грамм:\n"
        f"Например: 150",
        reply_markup=get_cancel_keyboard()
    )


@router.message(AddProductStates.waiting_for_grams, F.text == "❌ Отмена")
async def cancel_add_grams(message: Message, state: FSMContext):
    """Отмена ввода граммов"""
    await state.clear()
    await message.answer("❌ Добавление отменено", reply_markup=get_main_keyboard())


@router.message(AddProductStates.waiting_for_grams)
async def process_grams(message: Message, state: FSMContext, session: AsyncSession):
    """Обработка количества грамм"""
    # Проверяем, что введено число
    if not message.text.isdigit():
        await message.answer(
            "❌ Пожалуйста, введите число (только цифры)\n"
            "Например: 150",
            reply_markup=get_cancel_keyboard()
        )
        return

    grams = int(message.text)

    if grams <= 0 or grams > 10000:
        await message.answer(
            "❌ Количество грамм должно быть от 1 до 10000\n"
            "Попробуйте ещё раз:",
            reply_markup=get_cancel_keyboard()
        )
        return

    # Получаем данные из состояния
    data = await state.get_data()
    product = data.get("product")

    # Получаем пользователя
    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()

    if not user:
        user = User(telegram_id=message.from_user.id, daily_goal=2000)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    # Считаем калории
    calories = product.kcal_per_100g * grams / 100

    # Сохраняем в БД
    meal = Meal(
        user_id=user.id,
        product_name=product.name,
        grams=grams,
        calories=calories,
        date=date.today()
    )
    session.add(meal)
    await session.commit()

    # Получаем сумму калорий за сегодня
    today_result = await session.execute(
        select(func.sum(Meal.calories)).where(
            Meal.user_id == user.id,
            Meal.date == date.today()
        )
    )
    today_calories = today_result.scalar() or 0

    # Очищаем состояние
    await state.clear()

    # Проверяем превышение нормы
    if today_calories > user.daily_goal:
        status = f"⚠️ Превышение на {int(today_calories - user.daily_goal)} ккал"
    else:
        remaining = user.daily_goal - today_calories
        status = f"✅ Осталось: {int(remaining)} ккал"

    # Формируем ответ
    response = (
        f"✅ Продукт добавлен!\n\n"
        f"🍽️ {product.name.capitalize()}\n"
        f"⚖️ {grams} г\n"
        f"🔥 {int(calories)} ккал\n\n"
        f"📊 Сегодня: {int(today_calories)} / {user.daily_goal} ккал\n"
        f"{status}"
    )

    await message.answer(response, reply_markup=get_main_keyboard())


@router.message(F.text == "🗑️ Удалить продукт")
async def start_delete_product(message: Message, session: AsyncSession):
    """Начало удаления продукта"""
    # Получаем пользователя
    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("❌ Сначала добавьте хотя бы один продукт", reply_markup=get_main_keyboard())
        return

    # Получаем продукты за сегодня
    meals_result = await session.execute(
        select(Meal).where(
            Meal.user_id == user.id,
            Meal.date == date.today()
        ).order_by(Meal.id.desc())
    )
    meals = meals_result.scalars().all()

    if not meals:
        await message.answer("📭 Сегодня ещё нет добавленных продуктов", reply_markup=get_main_keyboard())
        return

    await message.answer(
        "🗑️ Выберите продукт для удаления:",
        reply_markup=get_delete_keyboard(meals)
    )


@router.callback_query(F.data.startswith("delete_"))
async def delete_product(callback: CallbackQuery, session: AsyncSession):
    """Удаление выбранного продукта"""
    meal_id = int(callback.data.split("_")[1])

    # Удаляем продукт
    await session.execute(
        delete(Meal).where(Meal.id == meal_id)
    )
    await session.commit()

    await callback.answer("✅ Продукт удалён")
    await callback.message.edit_text("✅ Продукт успешно удалён!")

    # Отправляем главное меню
    await callback.message.answer(
        "Что дальше?",
        reply_markup=get_main_keyboard()
    )


@router.callback_query(F.data == "cancel_delete")
async def cancel_delete(callback: CallbackQuery):
    """Отмена удаления"""
    await callback.answer()
    await callback.message.edit_text("❌ Удаление отменено")
    await callback.message.answer(
        "Что дальше?",
        reply_markup=get_main_keyboard()
    )


@router.message(F.text == "❌ Очистить день")
async def reset_day(message: Message, session: AsyncSession):
    """Очистить записи за сегодня"""
    result = await session.execute(
        select(User).where(User.telegram_id == message.from_user.id)
    )
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("❌ Пользователь не найден", reply_markup=get_main_keyboard())
        return

    # Проверяем, есть ли записи за сегодня
    meals_result = await session.execute(
        select(func.count(Meal.id)).where(
            Meal.user_id == user.id,
            Meal.date == date.today()
        )
    )
    count = meals_result.scalar() or 0

    if count == 0:
        await message.answer("📭 Сегодня нет записей для удаления", reply_markup=get_main_keyboard())
        return

    # Удаляем записи за сегодня
    await session.execute(
        delete(Meal).where(
            Meal.user_id == user.id,
            Meal.date == date.today()
        )
    )
    await session.commit()

    await message.answer(
        f"🗑️ Удалено продуктов: {count}\n"
        f"День очищен!",
        reply_markup=get_main_keyboard()
    )