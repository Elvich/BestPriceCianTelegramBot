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
from config.config import config

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
        print("   - apartments (объявления: staging + production)")
        print("   - metro_stations (станции метро)")
        print("   - price_history (история изменения цен)")
        print("   - filter_logs (логи фильтрации)")
        print("   - users (пользователи бота)")
        print("   - user_notifications (уведомления о новых квартирах)")
        print("   - user_apartment_reads (отметки о просмотре)")
        print("   - user_apartment_reactions (лайки/дизлайки)")
        print("   - expenses (устаревшая таблица)")
        print("\n💡 Теперь одна БД содержит и staging, и production данные")
        print("   Используйте поле is_staging для разделения")
        print("📱 Добавлена система уведомлений о новых квартирах")
        print("❤️ Добавлена система лайков и дизлайков квартир")
        print("   Дизлайкнутые квартиры исключаются из поиска")
        
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

async def recreate_tables():
    """Пересоздает все таблицы с нуля"""
    try:
        print("🔄 ПЕРЕСОЗДАНИЕ БАЗЫ ДАННЫХ")
        print("=" * 50)
        
        print("🗑️  Удаляем старые таблицы...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        print("✅ Старые таблицы удалены")
        
        print("\n🔧 Создаем новые таблицы с системой уведомлений...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Новые таблицы созданы!")
        print("\n📋 Созданные таблицы:")
        print("   - apartments (объявления с полями уведомлений)")
        print("   - metro_stations (станции метро)")
        print("   - price_history (история изменения цен)")
        print("   - filter_logs (логи фильтрации)")
        print("   - users (пользователи бота)")
        print("   - user_notifications (📱 уведомления)")
        print("   - user_apartment_reads (👁️ отметки просмотра)")
        print("   - user_apartment_reactions (лайки/дизлайки)")
        
        print("\n🎉 База данных готова к работе с системой уведомлений и реакций!")
        
    except Exception as e:
        print(f"❌ Ошибка при пересоздании таблиц: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "drop":
            asyncio.run(drop_tables())
        elif command == "recreate":
            asyncio.run(recreate_tables())
        else:
            print("Доступные команды:")
            print("  python init_db.py          - создать таблицы")
            print("  python init_db.py drop     - удалить таблицы")
            print("  python init_db.py recreate - пересоздать все таблицы")
    else:
        asyncio.run(create_tables())