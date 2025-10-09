from aiogram import Bot, Dispatcher, types
import asyncio
import sys
import os

# Добавляем путь к родительской директории для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Router import router
from config import config

async def main():
    """Основная функция запуска бота."""
    try:
        # Валидируем конфигурацию перед запуском
        config.validate()
        
        # Выводим информацию о конфигурации
        config.print_config()
        
        # Создаем бота и диспетчер
        bot = Bot(config.get_bot_token())
        dp = Dispatcher()
        dp.include_router(router)
        
        print("🚀 Запуск бота")
        await dp.start_polling(bot)
        
    except ValueError as e:
        print(f"❌ Ошибка конфигурации: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен пользователем")