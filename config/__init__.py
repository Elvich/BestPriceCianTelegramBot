"""
Модуль конфигурации и безопасности для BestPriceCianTelegramBot.

Этот пакет содержит:
- Config.py: Система управления конфигурацией
- .env: Переменные окружения (не в Git)
- .env.example: Шаблон переменных окружения
- SECURITY.md: Руководство по безопасности
- check_config.py: Диагностика конфигурации

Для использования:
    from config.Config import config
    config.validate()
"""

# Экспортируем основные компоненты для удобства импорта
from .config import config, Config

__all__ = ['config', 'Config']