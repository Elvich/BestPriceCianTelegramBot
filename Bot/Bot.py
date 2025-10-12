from aiogram import Bot, Dispatcher, types
from aiogram.exceptions import TelegramNetworkError, TelegramServerError
import asyncio
import sys
import os
import logging
from datetime import datetime

# Добавляем путь к родительской директории для импорта config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .router import router
from config import config
from .error_handlers import check_telegram_connection, NetworkMonitor

# Настройка логирования
def setup_logging():
    """Настройка логирования для бота"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Настраиваем логгер для aiogram
    aiogram_logger = logging.getLogger('aiogram')
    aiogram_logger.setLevel(logging.WARNING)  # Уменьшаем количество логов от aiogram
    
    # Настраиваем собственный логгер
    logger = logging.getLogger(__name__)
    return logger

async def main():
    """Основная функция запуска бота."""
    logger = setup_logging()
    
    try:
        logger.info("🚀 Запуск Telegram бота для поиска квартир")
        
        # Валидируем конфигурацию перед запуском
        config.validate()
        logger.info("✅ Конфигурация валидирована успешно")
        
        # Выводим информацию о конфигурации
        config.print_config()
        
        # Создаем бота и диспетчер
        bot = Bot(config.get_bot_token())
        dp = Dispatcher()
        dp.include_router(router)
        
        # Проверяем соединение с Telegram API
        logger.info("🔍 Проверяем соединение с Telegram API...")
        if not await check_telegram_connection(bot):
            logger.error("❌ Не удается подключиться к Telegram API. Проверьте интернет-соединение и токен бота.")
            sys.exit(1)
        
        # Создаем монитор сети
        network_monitor = NetworkMonitor(bot)
        
        # Сохраняем ссылку на монитор в диспетчере для использования в роутерах
        dp['network_monitor'] = network_monitor
        
        # Добавляем глобальную обработку ошибок для диспетчера
        @dp.error()
        async def error_handler(event, exception):
            logger.error(f"Критическая ошибка в диспетчере: {exception}")
            
            # Если это сетевая ошибка, логируем её отдельно
            if isinstance(exception, (TelegramNetworkError, TelegramServerError)):
                logger.warning(f"Сетевая ошибка Telegram: {exception}")
            else:
                logger.exception("Необработанное исключение в боте:")
            
            return True  # Говорим диспетчеру, что ошибка обработана
        
        logger.info("🚀 Бот готов к работе. Начинаем polling...")
        await dp.start_polling(bot, skip_updates=True)
        
    except ValueError as e:
        logger.error(f"❌ Ошибка конфигурации: {e}")
        sys.exit(1)
    except TelegramNetworkError as e:
        logger.error(f"❌ Сетевая ошибка при запуске бота: {e}")
        logger.info("Попробуйте перезапустить бота через несколько минут")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"❌ Неожиданная критическая ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("\n🛑 Бот остановлен пользователем")
    except Exception as e:
        logging.getLogger(__name__).exception(f"Критическая ошибка при запуске: {e}")