#!/usr/bin/env python3
"""
Демонстрационный скрипт для проверки настраиваемых параметров.
Показывает, как конфигурация изменяется через переменные окружения.
"""

import os
import sys

# Добавляем путь к родительской директории
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def demonstrate_default_config():
    """Показывает конфигурацию по умолчанию"""
    print("🔧 КОНФИГУРАЦИЯ ПО УМОЛЧАНИЮ")
    print("=" * 60)
    
    from config.config import config
    config.validate()
    config.print_config()
    
    from DB.filter_service import DEFAULT_FILTER_CONFIG, BARGAIN_HUNTER_CONFIG
    print("\n🎯 Конфигурации фильтров:")
    print(f"   Default Filter - Min Discount: {DEFAULT_FILTER_CONFIG.min_market_discount_percent}%")
    print(f"   Bargain Hunter - Min Discount: {BARGAIN_HUNTER_CONFIG.min_market_discount_percent}%")

def demonstrate_custom_config():
    """Показывает измененную конфигурацию через переменные окружения"""
    print("\n\n🔧 ИЗМЕНЕННАЯ КОНФИГУРАЦИЯ")
    print("=" * 60)
    
    # Изменяем переменные окружения
    os.environ['NOTIFICATION_CHECK_INTERVAL'] = '45'
    os.environ['MAX_NOTIFICATIONS_PER_BATCH'] = '100'
    os.environ['DEFAULT_FILTER_MIN_MARKET_DISCOUNT'] = '15.0'
    os.environ['BARGAIN_FILTER_MIN_MARKET_DISCOUNT'] = '25.0'
    os.environ['PARSER_DEFAULT_END_PAGE'] = '25'
    
    # Перезагружаем модули
    import importlib
    import config.config
    importlib.reload(config.config)
    
    import DB.filter_service
    importlib.reload(DB.filter_service)
    
    from config.config import config
    config.print_config()
    
    from DB.filter_service import DEFAULT_FILTER_CONFIG, BARGAIN_HUNTER_CONFIG
    print("\n🎯 Обновленные конфигурации фильтров:")
    print(f"   Default Filter - Min Discount: {DEFAULT_FILTER_CONFIG.min_market_discount_percent}%")
    print(f"   Bargain Hunter - Min Discount: {BARGAIN_HUNTER_CONFIG.min_market_discount_percent}%")

def show_all_configurable_parameters():
    """Показывает все настраиваемые параметры"""
    print("\n\n📋 ВСЕ НАСТРАИВАЕМЫЕ ПАРАМЕТРЫ")
    print("=" * 60)
    
    parameters = {
        "🔑 Основные настройки": [
            "BOT_TOKEN",
            "DATABASE_URL"
        ],
        "🕷️ Настройки парсера": [
            "PARSER_DELAY",
            "PARSER_DEEP_DELAY", 
            "PARSER_DEFAULT_START_PAGE",
            "PARSER_DEFAULT_END_PAGE"
        ],
        "🔗 API и сеть": [
            "REQUEST_TIMEOUT",
            "MAX_RETRIES",
            "NETWORK_RETRY_MAX_ATTEMPTS",
            "NETWORK_RETRY_BASE_DELAY",
            "NETWORK_RETRY_MAX_DELAY",
            "NETWORK_RETRY_EXPONENTIAL_BACKOFF"
        ],
        "🔔 Уведомления": [
            "NOTIFICATION_CHECK_INTERVAL",
            "NOTIFICATION_ERROR_RETRY_INTERVAL",
            "MAX_NOTIFICATIONS_PER_BATCH"
        ],
        "🎯 Фильтры - Основной": [
            "DEFAULT_FILTER_MAX_PRICE",
            "DEFAULT_FILTER_MIN_PRICE",
            "DEFAULT_FILTER_MIN_MARKET_DISCOUNT",
            "DEFAULT_FILTER_REQUIRED_METRO_DISTANCE",
            "DEFAULT_FILTER_MIN_TITLE_LENGTH"
        ],
        "💎 Фильтры - Премиум": [
            "PREMIUM_FILTER_MAX_PRICE",
            "PREMIUM_FILTER_MIN_PRICE",
            "PREMIUM_FILTER_MAX_PRICE_PER_SQM",
            "PREMIUM_FILTER_MIN_MARKET_DISCOUNT",
            "PREMIUM_FILTER_REQUIRED_METRO_DISTANCE",
            "PREMIUM_FILTER_MIN_AREA",
            "PREMIUM_FILTER_MIN_FLOOR",
            "PREMIUM_FILTER_MAX_FLOOR"
        ],
        "🎯 Фильтры - Охотник за скидками": [
            "BARGAIN_FILTER_MAX_PRICE",
            "BARGAIN_FILTER_MIN_PRICE", 
            "BARGAIN_FILTER_MIN_MARKET_DISCOUNT",
            "BARGAIN_FILTER_REQUIRED_METRO_DISTANCE",
            "BARGAIN_FILTER_MIN_TITLE_LENGTH"
        ],
        "🚀 Фильтры - Начальная загрузка": [
            "BOOTSTRAP_FILTER_MAX_PRICE",
            "BOOTSTRAP_FILTER_MIN_PRICE",
            "BOOTSTRAP_FILTER_MIN_TITLE_LENGTH"
        ]
    }
    
    for category, params in parameters.items():
        print(f"\n{category}:")
        for param in params:
            print(f"   {param}")
    
    print(f"\n📊 Всего настраиваемых параметров: {sum(len(params) for params in parameters.values())}")

if __name__ == "__main__":
    print("🏠 BESTPRICECIANTELEGRAMBOT - ДЕМОНСТРАЦИЯ НАСТРАИВАЕМЫХ ПАРАМЕТРОВ")
    print("=" * 80)
    
    # Показываем конфигурацию по умолчанию
    demonstrate_default_config()
    
    # Показываем измененную конфигурацию
    demonstrate_custom_config()
    
    # Показываем все параметры
    show_all_configurable_parameters()
    
    print("\n✅ Все параметры успешно настраиваются через переменные окружения!")
    print("📄 Проверьте файлы .env и .env.example для полной конфигурации")