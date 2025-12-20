"""
Сервис уведомлений для системы мониторинга квартир.
Отправляет пользователям уведомления о новых одобренных квартирах.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload

from .models import async_session, Apartment, UserNotification, User, UserApartmentRead
from .apartment_service import ApartmentService

logger = logging.getLogger(__name__)


class NotificationService:
    """Сервис для управления уведомлениями пользователей"""

    @staticmethod
    async def create_notifications_for_new_apartments(apartment_count: int) -> int:
        """
        Создает уведомления для всех активных пользователей о новых квартирах
        
        Args:
            apartment_count: Количество новых одобренных квартир
            
        Returns:
            Количество созданных уведомлений
        """
        if apartment_count <= 0:
            return 0

        async with async_session() as session:
            try:
                # Получаем всех активных пользователей
                query = select(User).where(User.is_active == True)
                result = await session.execute(query)
                active_users = result.scalars().all()

                if not active_users:
                    logger.info("Нет активных пользователей для отправки уведомлений")
                    return 0

                # Создаем уведомления для каждого пользователя
                notifications_created = 0
                
                for user in active_users:
                    # Формируем текст уведомления
                    if apartment_count == 1:
                        message = f"🏠 Найдена 1 новая квартира ниже рынка!"
                    elif apartment_count < 5:
                        message = f"🏠 Найдено {apartment_count} новые квартиры ниже рынка!"
                    else:
                        message = f"🏠 Найдено {apartment_count} новых квартир ниже рынка!"
                    
                    message += f"\n\n👆 Нажмите /start, чтобы посмотреть новые предложения"

                    # Создаем уведомление
                    notification = UserNotification(
                        telegram_id=user.telegram_id,
                        apartment_count=apartment_count,
                        message=message,
                        is_sent=False,
                        is_read=False
                    )
                    
                    session.add(notification)
                    notifications_created += 1

                await session.commit()
                logger.info(f"Создано {notifications_created} уведомлений для {apartment_count} новых квартир")
                return notifications_created

            except Exception as e:
                logger.error(f"Ошибка при создании уведомлений: {e}")
                await session.rollback()
                return 0

    @staticmethod
    async def get_pending_notifications(telegram_id: Optional[int] = None, limit: int = 100) -> List[UserNotification]:
        """
        Получает неотправленные уведомления
        
        Args:
            telegram_id: ID пользователя (если None, то для всех)
            limit: Максимальное количество уведомлений
            
        Returns:
            Список неотправленных уведомлений
        """
        async with async_session() as session:
            query = select(UserNotification).where(
                UserNotification.is_sent == False
            ).order_by(UserNotification.created_at)

            if telegram_id:
                query = query.where(UserNotification.telegram_id == telegram_id)

            query = query.limit(limit)
            result = await session.execute(query)
            return result.scalars().all()

    @staticmethod
    async def mark_notification_sent(notification_id: int) -> bool:
        """
        Отмечает уведомление как отправленное
        
        Args:
            notification_id: ID уведомления
            
        Returns:
            True если успешно обновлено
        """
        async with async_session() as session:
            try:
                query = select(UserNotification).where(UserNotification.id == notification_id)
                result = await session.execute(query)
                notification = result.scalar_one_or_none()

                if notification:
                    notification.is_sent = True
                    notification.sent_at = datetime.utcnow()
                    await session.commit()
                    return True

            except Exception as e:
                logger.error(f"Ошибка при обновлении уведомления {notification_id}: {e}")
                await session.rollback()

            return False

    @staticmethod
    async def mark_notifications_read(telegram_id: int) -> int:
        """
        Отмечает все уведомления пользователя как прочитанные
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            Количество отмеченных уведомлений
        """
        async with async_session() as session:
            try:
                query = select(UserNotification).where(
                    and_(
                        UserNotification.telegram_id == telegram_id,
                        UserNotification.is_read == False
                    )
                )
                result = await session.execute(query)
                notifications = result.scalars().all()

                marked_count = 0
                for notification in notifications:
                    notification.is_read = True
                    notification.read_at = datetime.utcnow()
                    marked_count += 1

                await session.commit()
                logger.info(f"Отмечено как прочитанные {marked_count} уведомлений для пользователя {telegram_id}")
                return marked_count

            except Exception as e:
                logger.error(f"Ошибка при отметке уведомлений как прочитанные: {e}")
                await session.rollback()
                return 0

    @staticmethod
    async def get_new_apartments_for_user(telegram_id: int, limit: int = 50) -> List[Apartment]:
        """
        Получает новые квартиры для пользователя (которые он еще не просматривал)
        
        Args:
            telegram_id: ID пользователя в Telegram
            limit: Максимальное количество квартир
            
        Returns:
            Список новых квартир
        """
        async with async_session() as session:
            # Подзапрос для получения ID просмотренных квартир
            read_apartments_subquery = select(UserApartmentRead.apartment_id).where(
                UserApartmentRead.telegram_id == telegram_id
            )

            # Основной запрос: новые квартиры, которые пользователь не просматривал
            query = select(Apartment).options(
                selectinload(Apartment.metro_stations),
                selectinload(Apartment.price_history)
            ).where(
                and_(
                    Apartment.is_active == True,
                    Apartment.is_staging == False,  # Только production квартиры
                    Apartment.is_new == True,       # Только новые
                    ~Apartment.id.in_(read_apartments_subquery)  # Не просмотренные пользователем
                )
            ).order_by(Apartment.approved_at.desc()).limit(limit)

            result = await session.execute(query)
            return result.scalars().all()

    @staticmethod
    async def mark_apartments_as_viewed(telegram_id: int, apartment_ids: List[int]) -> int:
        """
        Отмечает квартиры как просмотренные пользователем
        
        Args:
            telegram_id: ID пользователя в Telegram
            apartment_ids: Список ID квартир
            
        Returns:
            Количество отмеченных квартир
        """
        if not apartment_ids:
            return 0

        async with async_session() as session:
            try:
                marked_count = 0
                
                for apartment_id in apartment_ids:
                    # Проверяем, не отмечена ли уже квартира как просмотренная
                    existing_query = select(UserApartmentRead).where(
                        and_(
                            UserApartmentRead.telegram_id == telegram_id,
                            UserApartmentRead.apartment_id == apartment_id
                        )
                    )
                    existing_result = await session.execute(existing_query)
                    existing_read = existing_result.scalar_one_or_none()

                    if not existing_read:
                        # Создаем запись о просмотре
                        read_record = UserApartmentRead(
                            telegram_id=telegram_id,
                            apartment_id=apartment_id
                        )
                        session.add(read_record)
                        marked_count += 1

                await session.commit()
                logger.info(f"Отмечено как просмотренные {marked_count} квартир для пользователя {telegram_id}")
                return marked_count

            except Exception as e:
                logger.error(f"Ошибка при отметке квартир как просмотренные: {e}")
                await session.rollback()
                return 0

    @staticmethod
    async def get_notification_stats() -> Dict[str, int]:
        """
        Получает статистику по уведомлениям
        
        Returns:
            Словарь со статистикой
        """
        async with async_session() as session:
            try:
                # Общее количество уведомлений
                total_query = select(func.count(UserNotification.id))
                total_result = await session.execute(total_query)
                total_notifications = total_result.scalar() or 0

                # Отправленные уведомления
                sent_query = select(func.count(UserNotification.id)).where(UserNotification.is_sent == True)
                sent_result = await session.execute(sent_query)
                sent_notifications = sent_result.scalar() or 0

                # Прочитанные уведомления
                read_query = select(func.count(UserNotification.id)).where(UserNotification.is_read == True)
                read_result = await session.execute(read_query)
                read_notifications = read_result.scalar() or 0

                # Новые квартиры
                new_apartments_query = select(func.count(Apartment.id)).where(
                    and_(
                        Apartment.is_new == True,
                        Apartment.is_staging == False,
                        Apartment.is_active == True
                    )
                )
                new_apartments_result = await session.execute(new_apartments_query)
                new_apartments = new_apartments_result.scalar() or 0

                return {
                    'total_notifications': total_notifications,
                    'sent_notifications': sent_notifications,
                    'read_notifications': read_notifications,
                    'pending_notifications': total_notifications - sent_notifications,
                    'new_apartments': new_apartments
                }

            except Exception as e:
                logger.error(f"Ошибка при получении статистики уведомлений: {e}")
                return {
                    'total_notifications': 0,
                    'sent_notifications': 0,
                    'read_notifications': 0,
                    'pending_notifications': 0,
                    'new_apartments': 0
                }

    @staticmethod
    async def cleanup_old_notifications(days_old: int = 30) -> int:
        """
        Удаляет старые уведомления
        
        Args:
            days_old: Возраст уведомлений в днях для удаления
            
        Returns:
            Количество удаленных уведомлений
        """
        async with async_session() as session:
            try:
                cutoff_date = datetime.utcnow() - timedelta(days=days_old)
                
                query = select(UserNotification).where(
                    UserNotification.created_at < cutoff_date
                )
                result = await session.execute(query)
                old_notifications = result.scalars().all()

                deleted_count = 0
                for notification in old_notifications:
                    await session.delete(notification)
                    deleted_count += 1

                await session.commit()
                logger.info(f"Удалено {deleted_count} старых уведомлений (старше {days_old} дней)")
                return deleted_count

            except Exception as e:
                logger.error(f"Ошибка при очистке старых уведомлений: {e}")
                await session.rollback()
                return 0