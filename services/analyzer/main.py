
import asyncio
import sys
import os
import logging
from datetime import datetime

# Обеспечиваем корректные импорты core
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.config import config
from core.database.filter_service import FilterService, DEFAULT_FILTER_CONFIG

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), "analyzer.log"))
    ]
)
logger = logging.getLogger("AnalyzerService")

async def run_analyzer_service():
    """Запускает основной цикл анализатора"""
    logger.info("🚀 Запуск сервиса анализа...")
    
    # Инициализируем сервис фильтрации с конфигурацией по умолчанию
    filter_service = FilterService(DEFAULT_FILTER_CONFIG)
    logger.info(f"✅ Фильтр сервис инициализирован. Конфигурация: {DEFAULT_FILTER_CONFIG}")
    
    while True:
        try:
            logger.info("🔎 Поиск новых квартир в staging...")
            
            # Запускаем обработку квартир
            # Лимит можно вынести в конфиг, пока 50 за раз
            stats = await filter_service.process_apartments(limit=50)
            
            if stats['processed'] > 0:
                logger.info(f"📊 Результаты обработки: {stats}")
            elif stats['processed'] == 0:
                logger.debug("Нет новых квартир для обработки")
                
            # Пауза между циклами
            # Если были обработаны квартиры, пауза меньше, чтобы быстрее разгрести очередь
            delay = 10 if stats['processed'] > 0 else 60
            
            logger.debug(f"⏳ Ожидание {delay} сек...")
            await asyncio.sleep(delay)
            
        except Exception as e:
            logger.critical(f"🔥 Критическая ошибка в сервисе анализа: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(run_analyzer_service())
    except KeyboardInterrupt:
        logger.info("🛑 Сервис остановлен пользователем")
