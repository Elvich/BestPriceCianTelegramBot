"""
Утилиты для обработки ошибок и повторных попыток
"""
import asyncio
import logging
from functools import wraps
from typing import Callable, Any, Optional
from aiogram.exceptions import TelegramNetworkError, TelegramServerError, TelegramBadRequest

logger = logging.getLogger(__name__)

class RetryConfig:
    """Конфигурация для повторных попыток"""
    def __init__(self, max_retries: int = None, base_delay: float = None, max_delay: float = None, exponential_backoff: bool = None):
        # Импортируем config здесь, чтобы избежать циклических импортов
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from config import config
        
        self.max_retries = max_retries if max_retries is not None else config.NETWORK_RETRY_MAX_ATTEMPTS
        self.base_delay = base_delay if base_delay is not None else config.NETWORK_RETRY_BASE_DELAY
        self.max_delay = max_delay if max_delay is not None else config.NETWORK_RETRY_MAX_DELAY
        self.exponential_backoff = exponential_backoff if exponential_backoff is not None else config.NETWORK_RETRY_EXPONENTIAL_BACKOFF

async def retry_on_network_error(
    func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> Any:
    """
    Повторяет выполнение функции при сетевых ошибках
    """
    if config is None:
        config = RetryConfig()
    
    last_exception = None
    
    for attempt in range(config.max_retries + 1):
        try:
            return await func(*args, **kwargs)
        
        except (TelegramNetworkError, TelegramServerError) as e:
            last_exception = e
            
            if attempt == config.max_retries:
                logger.error(f"Не удалось выполнить {func.__name__} после {config.max_retries} попыток. Последняя ошибка: {e}")
                raise e
            
            # Вычисляем задержку
            if config.exponential_backoff:
                delay = min(config.base_delay * (2 ** attempt), config.max_delay)
            else:
                delay = config.base_delay
            
            logger.warning(f"Сетевая ошибка в {func.__name__} (попытка {attempt + 1}/{config.max_retries + 1}): {e}. Повтор через {delay:.1f}с")
            await asyncio.sleep(delay)
            continue
            
        except TelegramBadRequest as e:
            # Для TelegramBadRequest не делаем повторы, это обычно ошибки логики
            if "message is not modified" in str(e).lower():
                logger.debug(f"Сообщение не изменилось в {func.__name__}: {e}")
                return None  # Это нормально, возвращаем None
            else:
                logger.error(f"Ошибка в запросе к Telegram API в {func.__name__}: {e}")
                raise e
                
        except Exception as e:
            logger.error(f"Неожиданная ошибка в {func.__name__}: {e}")
            raise e
    
    # Этот код никогда не должен выполниться, но на всякий случай
    if last_exception:
        raise last_exception

def network_retry(config: Optional[RetryConfig] = None):
    """
    Декоратор для повторных попыток при сетевых ошибках
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await retry_on_network_error(func, *args, config=config, **kwargs)
        return wrapper
    return decorator

async def check_telegram_connection(bot) -> bool:
    """
    Проверяет соединение с Telegram API
    """
    try:
        me = await bot.get_me()
        logger.info(f"✅ Соединение с Telegram API в порядке. Бот: @{me.username}")
        return True
    except Exception as e:
        logger.error(f"❌ Не удается подключиться к Telegram API: {e}")
        return False

class NetworkMonitor:
    """Мониторинг состояния сети"""
    
    def __init__(self, bot):
        self.bot = bot
        self.last_successful_request = None
        self.consecutive_failures = 0
        
    async def log_request_success(self):
        """Логирует успешный запрос"""
        import datetime
        self.last_successful_request = datetime.datetime.now()
        if self.consecutive_failures > 0:
            logger.info(f"✅ Соединение восстановлено после {self.consecutive_failures} неудачных попыток")
            self.consecutive_failures = 0
    
    async def log_request_failure(self, error: Exception):
        """Логирует неудачный запрос"""
        self.consecutive_failures += 1
        
        if self.consecutive_failures >= 5:
            logger.warning(f"⚠️ {self.consecutive_failures} последовательных сетевых ошибок. Возможны проблемы с подключением к Telegram")
        
        # Каждые 10 неудач проверяем базовое соединение
        if self.consecutive_failures % 10 == 0:
            logger.info("🔍 Проверяем базовое соединение с Telegram API...")
            await check_telegram_connection(self.bot)