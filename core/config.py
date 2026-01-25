
"""
Модуль конфигурации приложения.
Загружает настройки из переменных окружения с использованием .env файла.
"""

import os
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# Определяем путь к .env файлу в корне проекта (на уровень выше core)
config_dir = Path(__file__).parent.parent
env_file = config_dir / '.env'

# Загружаем переменные из .env файла
load_dotenv(env_file)


class Config:
    """Класс для управления конфигурацией приложения."""
    
    # Telegram Bot Configuration
    BOT_TOKEN: str = os.getenv('BOT_TOKEN', '')

    # Cian URLs
    _CIAN_URLS_STR = os.getenv('CIAN_URLS', '')
    CIAN_URLS: list[str] = [url.strip() for url in _CIAN_URLS_STR.split(',') if url.strip()]

    
    # Database Configuration
    # DATABASE_URL: str = os.getenv('DATABASE_URL', 'sqlite+aiosqlite:///dp.sqlite') # Original line
    
    # Database
    _DATABASE_URL_RAW = os.getenv("DATABASE_URL")
    if not _DATABASE_URL_RAW:
        pg_user = os.getenv("POSTGRES_USER", "postgres")
        pg_password = os.getenv("POSTGRES_PASSWORD", "postgres")
        pg_host = os.getenv("POSTGRES_HOST", "db") # 'db' - имя сервиса в docker-compose
        pg_port = os.getenv("POSTGRES_PORT", "5432")
        pg_db = os.getenv("POSTGRES_DB", "cian_bot")
        
        # Если есть хоть один спец-параметр, формируем URL для PG
        if os.getenv("POSTGRES_USER") or os.getenv("POSTGRES_DB"):
             DATABASE_URL: str = f"postgresql+asyncpg://{pg_user}:{pg_password}@{pg_host}:{pg_port}/{pg_db}"
        else:
             # Fallback to SQLite default if nothing configured
             DATABASE_URL: str = "sqlite+aiosqlite:///cian_bot.db"
    else:
        DATABASE_URL: str = _DATABASE_URL_RAW
    
    # Parser Configuration
    PARSER_DELAY: int = int(os.getenv('PARSER_DELAY', '3'))
    MIN_PARSER_DELAY: float = float(os.getenv('MIN_PARSER_DELAY', '5.0'))
    MAX_PARSER_DELAY: float = float(os.getenv('MAX_PARSER_DELAY', '15.0'))
    PARSER_DEEP_DELAY: int = int(os.getenv('PARSER_DEEP_DELAY', '2'))
    PARSER_DEFAULT_START_PAGE: int = int(os.getenv('PARSER_DEFAULT_START_PAGE', '1'))
    PARSER_DEFAULT_END_PAGE: int = int(os.getenv('PARSER_DEFAULT_END_PAGE', '17'))
    
    # Auto Parser Configuration
    AUTO_PARSER_CYCLE_DELAY: int = int(os.getenv('AUTO_PARSER_CYCLE_DELAY', '1800'))  # 30 минут между циклами
    
    # API Configuration
    REQUEST_TIMEOUT: int = int(os.getenv('REQUEST_TIMEOUT', '60'))
    MAX_RETRIES: int = int(os.getenv('MAX_RETRIES', '10'))
    PROXY_URL: Optional[str] = os.getenv('PROXY_URL')
    PROXY_LIST: list[str] = [p.strip() for p in os.getenv('PROXY_LIST', '').split(',') if p.strip()]
    PROXY_FILE_PATH: str = os.getenv('PROXY_FILE_PATH', 'proxies.txt')
    PROXY_CHECK_URL: str = os.getenv('PROXY_CHECK_URL', 'https://www.cian.ru')
    # Public proxy sources
    PROXY_PUBLIC_SOURCES: list[str] = [
        'https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt',
        'https://raw.githubusercontent.com/hookzof/socks5_list/master/proxy.txt',
        'https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt',
        'https://raw.githubusercontent.com/zloi-user/hideip.me/main/socks5.txt',
        'https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/socks5.txt'
    ]
    VERIFY_SSL: bool = os.getenv('VERIFY_SSL', 'True').lower() == 'true'
    
    # Bot Notification Settings
    NOTIFICATION_CHECK_INTERVAL: int = int(os.getenv('NOTIFICATION_CHECK_INTERVAL', '30'))
    NOTIFICATION_ERROR_RETRY_INTERVAL: int = int(os.getenv('NOTIFICATION_ERROR_RETRY_INTERVAL', '60'))
    MAX_NOTIFICATIONS_PER_BATCH: int = int(os.getenv('MAX_NOTIFICATIONS_PER_BATCH', '50'))
    
    # Network Retry Configuration
    NETWORK_RETRY_MAX_ATTEMPTS: int = int(os.getenv('NETWORK_RETRY_MAX_ATTEMPTS', '3'))
    NETWORK_RETRY_BASE_DELAY: float = float(os.getenv('NETWORK_RETRY_BASE_DELAY', '1.0'))
    NETWORK_RETRY_MAX_DELAY: float = float(os.getenv('NETWORK_RETRY_MAX_DELAY', '60.0'))
    NETWORK_RETRY_EXPONENTIAL_BACKOFF: bool = os.getenv('NETWORK_RETRY_EXPONENTIAL_BACKOFF', 'true').lower() == 'true'
    
    # Filter Configuration - Default Filter
    DEFAULT_FILTER_MAX_PRICE: int = int(os.getenv('DEFAULT_FILTER_MAX_PRICE', '100000000'))
    DEFAULT_FILTER_MIN_PRICE: int = int(os.getenv('DEFAULT_FILTER_MIN_PRICE', '5000000'))
    DEFAULT_FILTER_MIN_MARKET_DISCOUNT: float = float(os.getenv('DEFAULT_FILTER_MIN_MARKET_DISCOUNT', '10.0'))
    DEFAULT_FILTER_REQUIRED_METRO_DISTANCE: int = int(os.getenv('DEFAULT_FILTER_REQUIRED_METRO_DISTANCE', '10'))
    DEFAULT_FILTER_MIN_TITLE_LENGTH: int = int(os.getenv('DEFAULT_FILTER_MIN_TITLE_LENGTH', '20'))
    
    # Filter Configuration - Premium Filter
    PREMIUM_FILTER_MAX_PRICE: int = int(os.getenv('PREMIUM_FILTER_MAX_PRICE', '80000000'))
    PREMIUM_FILTER_MIN_PRICE: int = int(os.getenv('PREMIUM_FILTER_MIN_PRICE', '20000000'))
    PREMIUM_FILTER_MAX_PRICE_PER_SQM: int = int(os.getenv('PREMIUM_FILTER_MAX_PRICE_PER_SQM', '400000'))
    PREMIUM_FILTER_MIN_MARKET_DISCOUNT: float = float(os.getenv('PREMIUM_FILTER_MIN_MARKET_DISCOUNT', '15.0'))
    PREMIUM_FILTER_REQUIRED_METRO_DISTANCE: int = int(os.getenv('PREMIUM_FILTER_REQUIRED_METRO_DISTANCE', '8'))
    PREMIUM_FILTER_MIN_AREA: float = float(os.getenv('PREMIUM_FILTER_MIN_AREA', '50.0'))
    PREMIUM_FILTER_MIN_FLOOR: int = int(os.getenv('PREMIUM_FILTER_MIN_FLOOR', '2'))
    PREMIUM_FILTER_MAX_FLOOR: int = int(os.getenv('PREMIUM_FILTER_MAX_FLOOR', '20'))
    
    # Filter Configuration - Bargain Hunter
    BARGAIN_FILTER_MAX_PRICE: int = int(os.getenv('BARGAIN_FILTER_MAX_PRICE', '150000000'))
    BARGAIN_FILTER_MIN_PRICE: int = int(os.getenv('BARGAIN_FILTER_MIN_PRICE', '3000000'))
    BARGAIN_FILTER_MIN_MARKET_DISCOUNT: float = float(os.getenv('BARGAIN_FILTER_MIN_MARKET_DISCOUNT', '20.0'))
    BARGAIN_FILTER_REQUIRED_METRO_DISTANCE: int = int(os.getenv('BARGAIN_FILTER_REQUIRED_METRO_DISTANCE', '30'))
    BARGAIN_FILTER_MIN_TITLE_LENGTH: int = int(os.getenv('BARGAIN_FILTER_MIN_TITLE_LENGTH', '15'))
    
    # Filter Configuration - Bootstrap
    BOOTSTRAP_FILTER_MAX_PRICE: int = int(os.getenv('BOOTSTRAP_FILTER_MAX_PRICE', '200000000'))
    BOOTSTRAP_FILTER_MIN_PRICE: int = int(os.getenv('BOOTSTRAP_FILTER_MIN_PRICE', '1000000'))
    BOOTSTRAP_FILTER_MIN_TITLE_LENGTH: int = int(os.getenv('BOOTSTRAP_FILTER_MIN_TITLE_LENGTH', '5'))
    
    @classmethod
    def validate(cls) -> None:
        """Валидация критически важных настроек."""
        if not cls.BOT_TOKEN:
            raise ValueError(
                "BOT_TOKEN не найден в переменных окружения. "
                "Убедитесь, что файл .env существует и содержит BOT_TOKEN."
            )
    
    @classmethod
    def get_bot_token(cls) -> str:
        """Получить токен бота с валидацией."""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN не установлен")
        return cls.BOT_TOKEN
    
    @classmethod
    def print_config(cls) -> None:
        """Вывести текущую конфигурацию (без чувствительных данных)."""
        print("📋 Текущая конфигурация:")
        print(f"   Bot Token: {'✅ Установлен' if cls.BOT_TOKEN else '❌ Не установлен'}")
        print(f"   Database URL: {cls.DATABASE_URL}")
        print("")
        print("🕷️  Настройки парсера:")
        print(f"   Parser Delay: {cls.PARSER_DELAY}s")
        print(f"   Deep Parse Delay: {cls.PARSER_DEEP_DELAY}s")
        print(f"   Default Pages: {cls.PARSER_DEFAULT_START_PAGE}-{cls.PARSER_DEFAULT_END_PAGE}")
        print(f"   Auto Parser Cycle Delay: {cls.AUTO_PARSER_CYCLE_DELAY}s ({cls.AUTO_PARSER_CYCLE_DELAY/60:.1f}min)")
        print("")
        print("🔗 API настройки:")
        print(f"   Request Timeout: {cls.REQUEST_TIMEOUT}s")
        print(f"   Max Retries: {cls.MAX_RETRIES}")
        print(f"   Network Retry Max Delay: {cls.NETWORK_RETRY_MAX_DELAY}s")
        print("")
        print("🔔 Настройки уведомлений:")
        print(f"   Check Interval: {cls.NOTIFICATION_CHECK_INTERVAL}s")
        print(f"   Max Notifications per Batch: {cls.MAX_NOTIFICATIONS_PER_BATCH}")
        print("")
        print("🎯 Фильтры по умолчанию:")
        print(f"   Min Market Discount: {cls.DEFAULT_FILTER_MIN_MARKET_DISCOUNT}%")
        print(f"   Price Range: {cls.DEFAULT_FILTER_MIN_PRICE:,} - {cls.DEFAULT_FILTER_MAX_PRICE:,} ₽")
        print(f"   Max Metro Distance: {cls.DEFAULT_FILTER_REQUIRED_METRO_DISTANCE} мин")


# Создаем экземпляр конфигурации
config = Config()

# Экспортируем для обратной совместимости
bot_token = config.get_bot_token