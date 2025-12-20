import logging
import sys
import os
from functools import wraps
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest

# Добавляем путь к корневой директории, если он еще не добавлен
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from core.database.user_service import UserService
from services.bot.handlers.error_handlers import network_retry, RetryConfig

logger = logging.getLogger(__name__)

# Конфигурация для повторных попыток
RETRY_CONFIG = RetryConfig()

# Декоратор для обработки сетевых ошибок и автоматического создания пользователей
def handle_network_errors(func):
    @wraps(func)
    @network_retry(config=RETRY_CONFIG)
    async def wrapper(*args, **kwargs):
        try:
            # Автоматически создаем/обновляем пользователя при каждом взаимодействии
            if args:
                if hasattr(args[0], 'from_user'):  # Message или CallbackQuery
                    user = args[0].from_user
                    await UserService.get_or_create_user(
                        telegram_id=user.id,
                        username=user.username,
                        first_name=user.first_name,
                        last_name=user.last_name
                    )
                    
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            
            # Попытаемся уведомить пользователя о проблеме
            try:
                if args and hasattr(args[0], 'answer'):
                    await args[0].answer("❌ Произошла ошибка. Попробуйте позже.")
                elif args and hasattr(args[0], 'message') and hasattr(args[0].message, 'answer'):
                    await args[0].message.answer("❌ Произошла ошибка. Попробуйте позже.")
            except:
                pass  # Если не удается отправить сообщение, просто игнорируем
            
            raise e  # Пробрасываем ошибку дальше
    return wrapper

# Функция для безопасного редактирования сообщений
async def safe_edit_message(callback, text, **kwargs):
    """Безопасное редактирование сообщения с проверкой на дублирование контента"""
    try:
        # Проверяем, изменился ли текст сообщения
        if hasattr(callback.message, 'text') and callback.message.text == text:
            # Если текст не изменился, просто отвечаем на callback
            await callback.answer()
            return
        
        await callback.message.edit_text(text, **kwargs)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            # Сообщение не изменилось, просто отвечаем на callback
            await callback.answer()
        else:
            # Другая ошибка, пробуем отправить новое сообщение
            await callback.message.answer(text, **kwargs)
    except Exception as e:
        logger.error(f"Error in safe_edit_message: {e}")
        await callback.answer("❌ Ошибка при обновлении сообщения")
