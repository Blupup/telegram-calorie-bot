import json
import os
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Product


async def load_products(session: AsyncSession):
    """Загрузить продукты из JSON файла в базу данных"""
    json_path = os.path.join("data", "products.json")

    if not os.path.exists(json_path):
        print("⚠️ Файл products.json не найден")
        return

    with open(json_path, "r", encoding="utf-8") as f:
        products_data = json.load(f)

    loaded_count = 0
    skipped_count = 0

    for item in products_data:
        # Проверяем, есть ли уже такой продукт
        result = await session.execute(
            select(Product).where(Product.name == item["name"])
        )
        existing = result.scalar_one_or_none()

        if existing:
            skipped_count += 1
            continue

        # Добавляем новый продукт
        product = Product(
            name=item["name"],
            kcal_per_100g=item["kcal_per_100g"]
        )
        session.add(product)
        loaded_count += 1

    await session.commit()

    print(f"✅ Загружено продуктов: {loaded_count}")
    print(f"⏭️ Пропущено (уже существуют): {skipped_count}")