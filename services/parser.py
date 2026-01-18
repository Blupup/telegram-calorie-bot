import re
from typing import Optional, Dict


def parse_meal_input(text: str) -> Optional[Dict[str, any]]:
    """
    Парсит ввод пользователя для добавления продукта

    Поддерживаемые форматы:
    - яблоко 150
    - яблоко 150 г
    - яблоко 150г
    - яблоко 150гр
    - /add яблоко 150

    Args:
        text: входная строка от пользователя

    Returns:
        dict с ключами 'product' и 'grams' или None
    """
    # Убираем команду /add если есть
    text = text.strip()
    if text.lower().startswith('/add'):
        text = text[4:].strip()

    # Паттерн: название продукта + число + опционально единицы измерения
    # Ищем последнее число в строке
    pattern = r'^(.+?)\s+(\d+)\s*(?:г|гр|грамм|граммов)?\.?$'
    match = re.match(pattern, text, re.IGNORECASE)

    if match:
        product_name = match.group(1).strip().lower()
        grams = int(match.group(2))

        return {
            "product": product_name,
            "grams": grams
        }

    return None