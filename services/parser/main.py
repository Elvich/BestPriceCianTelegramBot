
import asyncio
import sys
import os
import random
import logging
from datetime import datetime

# Обеспечиваем корректные импорты core
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.config import config
from core.database.apartment_service import ApartmentService
from services.parser.logic.cian_parser import CianParser

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(os.path.dirname(os.path.abspath(__file__)), "parser.log"))
    ]
)
logger = logging.getLogger("ParserService")

async def run_parser_service():
    """Запускает основной цикл парсера"""
    logger.info("🚀 Запуск сервиса парсинга...")
    
    parser = CianParser()
    
    while True:
        try:
            # Получаем URL для парсинга из конфига
            urls = config.CIAN_URLS
            if not urls:
                logger.warning("⚠️ Не заданы URL для парсинга в конфиге!")
                await asyncio.sleep(60)
                continue
                
            for url_index, url in enumerate(urls):
                logger.info(f"🔎 Обработка URL {url_index + 1}/{len(urls)}")
                
                try:
                    # 1. Парсинг
                    # TODO: В будущем добавить пагинацию. Сейчас парсим только первую страницу для скорости/тестов,
                    # как было в оригинале, или можно расширить.
                    # В оригинальном auto_parser.py использовался зацикленный вызов parsing(url), но там логика
                    # была смешана. Здесь мы вызываем метод парсера.
                    
                    found_apartments = parser.parse_page(url)
                    logger.info(f"✅ Найдено {len(found_apartments)} объявлений")
                    
                    if found_apartments:
                        # 2. Сохранение в Staging
                        # Используем save_to_staging, который помечает is_staging=True и filter_status='pending'
                        stats = await ApartmentService.save_to_staging(found_apartments, source_url=url)
                        
                        logger.info(f"💾 Результаты сохранения: {stats}")
                        
                        # 3. Маркировка неактивных
                        # Получаем список ID, которые были найдены в этом проходе
                        found_ids = [ApartmentService.extract_cian_id(apt[0]) for apt in found_apartments]
                        if found_ids:
                             # ВАЖНО: Маркировка неактивных сложнее в мульти-страничном парсинге.
                             # Если мы парсим только 1 страницу, то не должны помечать неактивными те, 
                             # что ушли на 2 страницу.
                             # Пока пропускаем этот шаг или нужно быть очень осторожным.
                             # В оригинале не было явной деактивации в auto_parser.py (только добавление).
                             pass

                except Exception as e:
                    logger.error(f"❌ Ошибка при обработке URL {url}: {e}")
                
                # Пауза между URL
                delay = random.uniform(config.MIN_PARSER_DELAY, config.MAX_PARSER_DELAY)
                logger.info(f"⏳ Ожидание {delay:.1f} сек...")
                await asyncio.sleep(delay)
            
            # Пауза между полными циклами
            cycle_delay = config.AUTO_PARSER_CYCLE_DELAY
            logger.info(f"😴 Цикл завершен. Пауза {cycle_delay} сек...")
            await asyncio.sleep(cycle_delay)
            
        except Exception as e:
            logger.critical(f"🔥 Критическая ошибка в сервисе: {e}")
            await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(run_parser_service())
    except KeyboardInterrupt:
        logger.info("🛑 Сервис остановлен пользователем")
