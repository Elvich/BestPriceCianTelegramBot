"""
Скрипт для создания таблиц в базе данных.
Запускайте этот скрипт перед первым использованием проекта.
"""

import asyncio
import sys
import os

# Добавляем путь к корневой директории
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DB.Models import Base, engine
from config import config

async def create_tables():
    """Создает все таблицы в базе данных"""
    try:
        print("🔧 Инициализация базы данных...")
        print(f"   Database URL: {config.DATABASE_URL}")
        
        # Создаем все таблицы
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Таблицы успешно созданы!")
        print("\nСозданные таблицы:")
        print("   - apartments (объявления о квартирах)")
        print("   - metro_stations (станции метро)")
        print("   - price_history (история изменения цен)")
        print("   - users (пользователи бота)")
        print("   - expenses (устаревшая таблица)")
        
    except Exception as e:
        print(f"❌ Ошибка при создании таблиц: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()

async def drop_tables():
    """Удаляет все таблицы (осторожно!)"""
    try:
        print("⚠️  ВНИМАНИЕ: Удаление всех таблиц...")
        response = input("Вы уверены? Введите 'yes' для подтверждения: ")
        
        if response.lower() != 'yes':
            print("Операция отменена.")
            return
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        
        print("✅ Таблицы удалены!")
        
    except Exception as e:
        print(f"❌ Ошибка при удалении таблиц: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "drop":
        asyncio.run(drop_tables())
    else:
        asyncio.run(create_tables())