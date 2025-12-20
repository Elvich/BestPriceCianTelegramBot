"""
Сервис рассылки уведомлений через Telegram бота.
Отправляет пользователям push-уведомления о новых квартирах.
"""

import asyncio
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramNetworkError

from core.database.notification_service import NotificationService
from core.database.models import UserNotification

logger = logging.getLogger(__name__)


class NotificationSender:
    """Класс для отправки уведомлений пользователям через Telegram"""

    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_pending_notifications(self, max_notifications: int = 100) -> dict:
        """
        Отправляет все неотправленные уведомления
        
        Args:
            max_notifications: Максимальное количество уведомлений для отправки за раз
            
        Returns:
            Статистика отправки: {'sent': int, 'failed': int, 'errors': list}
        """
        stats = {'sent': 0, 'failed': 0, 'errors': []}
        
        try:
            # Получаем неотправленные уведомления
            pending_notifications = await NotificationService.get_pending_notifications(
                limit=max_notifications
            )
            
            if not pending_notifications:
                logger.info("Нет неотправленных уведомлений")
                return stats
                
            logger.info(f"Найдено {len(pending_notifications)} неотправленных уведомлений")
            
            # Отправляем каждое уведомление
            for notification in pending_notifications:
                try:
                    await self._send_notification(notification)
                    
                    # Отмечаем как отправленное
                    await NotificationService.mark_notification_sent(notification.id)
                    stats['sent'] += 1
                    
                    # Небольшая задержка между отправками
                    await asyncio.sleep(0.1)
                    
                except (TelegramForbiddenError, TelegramBadRequest) as e:
                    error_msg = f"Ошибка отправки пользователю {notification.telegram_id}: {e}"
                    logger.warning(error_msg)
                    stats['errors'].append(error_msg)
                    stats['failed'] += 1
                    
                    # Помечаем как отправленное, чтобы не пытаться снова
                    await NotificationService.mark_notification_sent(notification.id)
                    
                except Exception as e:
                    error_msg = f"Неожиданная ошибка при отправке уведомления {notification.id}: {e}"
                    logger.error(error_msg)
                    stats['errors'].append(error_msg)
                    stats['failed'] += 1
                    
            logger.info(f"Отправка завершена: {stats['sent']} успешно, {stats['failed']} с ошибками")
            return stats
            
        except Exception as e:
            error_msg = f"Критическая ошибка при отправке уведомлений: {e}"
            logger.error(error_msg)
            stats['errors'].append(error_msg)
            return stats

    async def _send_notification(self, notification: UserNotification):
        """
        Отправляет одно уведомление пользователю
        
        Args:
            notification: Объект уведомления для отправки
        """
        try:
            # Формируем кнопку для быстрого перехода к новым квартирам
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🆕 Посмотреть новые квартиры", 
                    callback_data="recent"
                )]
            ])
            
            await self.bot.send_message(
                chat_id=notification.telegram_id,
                text=notification.message,
                reply_markup=keyboard
            )
            
            logger.debug(f"Уведомление отправлено пользователю {notification.telegram_id}")
            
        except TelegramForbiddenError:
            # Пользователь заблокировал бота или удалил чат
            logger.warning(f"Пользователь {notification.telegram_id} заблокировал бота")
            raise
            
        except TelegramBadRequest as e:
            # Неверный chat_id или другие проблемы с запросом
            logger.warning(f"Неверный запрос для пользователя {notification.telegram_id}: {e}")
            raise
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления пользователю {notification.telegram_id}: {e}")
            raise

    async def send_notification_to_user(self, telegram_id: int, message: str, 
                                      show_new_button: bool = True) -> bool:
        """
        Отправляет персональное уведомление конкретному пользователю
        
        Args:
            telegram_id: ID пользователя в Telegram
            message: Текст уведомления
            show_new_button: Показывать ли кнопку "Новые квартиры"
            
        Returns:
            True если уведомление отправлено успешно
        """
        try:
            keyboard = None
            if show_new_button:
                from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(
                        text="🆕 Посмотреть новые квартиры", 
                        callback_data="recent"
                    )]
                ])
            
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message,
                reply_markup=keyboard
            )
            
            logger.info(f"Персональное уведомление отправлено пользователю {telegram_id}")
            return True
            
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            logger.warning(f"Не удалось отправить уведомление пользователю {telegram_id}: {e}")
            return False
            
        except Exception as e:
            logger.error(f"Ошибка отправки персонального уведомления: {e}")
            return False

    async def get_sending_stats(self) -> dict:
        """
        Получает статистику отправки уведомлений
        
        Returns:
            Статистика уведомлений
        """
        try:
            return await NotificationService.get_notification_stats()
        except Exception as e:
            logger.error(f"Ошибка получения статистики уведомлений: {e}")
            return {
                'total_notifications': 0,
                'sent_notifications': 0,
                'read_notifications': 0,
                'pending_notifications': 0,
                'new_apartments': 0
            }