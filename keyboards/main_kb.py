from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Главная клавиатура бота"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➕ Добавить продукт"),
                KeyboardButton(text="📊 Статистика дня")
            ],
            [
                KeyboardButton(text="🎯 Моя норма"),
                KeyboardButton(text="📈 Общая статистика")
            ],
            [
                KeyboardButton(text="🗑️ Удалить продукт"),
                KeyboardButton(text="❌ Очистить день")
            ]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )
    return keyboard


def get_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с кнопкой отмены"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")]
        ],
        resize_keyboard=True
    )
    return keyboard


def get_delete_keyboard(meals: list) -> InlineKeyboardMarkup:
    """Клавиатура для удаления продуктов"""
    buttons = []

    for meal in meals:
        button = InlineKeyboardButton(
            text=f"🗑️ {meal.product_name.capitalize()} ({meal.grams}г)",
            callback_data=f"delete_{meal.id}"
        )
        buttons.append([button])

    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_delete")])

    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard