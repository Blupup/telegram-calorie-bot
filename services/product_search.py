import difflib
from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Product


async def find_product(session: AsyncSession, product_name: str) -> Optional[Product]:
    """
    Поиск продукта по точному совпадению

    Args:
        session: сессия БД
        product_name: название продукта (в нижнем регистре)

    Returns:
        Product или None
    """
    result = await session.execute(
        select(Product).where(Product.name == product_name.lower())
    )
    return result.scalar_one_or_none()


async def find_similar_products(session: AsyncSession, product_name: str, limit: int = 5) -> List[str]:
    """
    Поиск похожих продуктов используя difflib

    Args:
        session: сессия БД
        product_name: название продукта
        limit: максимальное количество предложений

    Returns:
        список похожих названий продуктов
    """
    # Получаем все названия продуктов
    result = await session.execute(select(Product.name))
    all_products = [row[0] for row in result.all()]

    # Ищем похожие используя difflib
    matches = difflib.get_close_matches(
        product_name.lower(),
        all_products,
        n=limit,
        cutoff=0.6
    )

    return matches