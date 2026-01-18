from aiogram.fsm.state import State, StatesGroup


class AddProductStates(StatesGroup):
    """Состояния для добавления продукта"""
    waiting_for_product = State()
    waiting_for_grams = State()


class SetGoalStates(StatesGroup):
    """Состояния для установки нормы"""
    waiting_for_goal = State()