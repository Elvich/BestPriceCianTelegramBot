"""
Сервис для управления пользователями бота
"""

import logging
from typing import Optional
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.dialects.sqlite import insert

from .models import async_session, User

logger = logging.getLogger(__name__)


class UserService:
    """Сервис для работы с пользователями бота"""

    @staticmethod
    async def get_or_create_user(
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None
    ) -> User:
        """
        Получает пользователя или создает нового если не существует
        
        Args:
            telegram_id: ID пользователя в Telegram
            username: Username пользователя
            first_name: Имя пользователя
            last_name: Фамилия пользователя
            
        Returns:
            Объект пользователя
        """
        async with async_session() as session:
            try:
                # Ищем существующего пользователя
                query = select(User).where(User.telegram_id == telegram_id)
                result = await session.execute(query)
                user = result.scalar_one_or_none()

                if user:
                    # Обновляем информацию о пользователе если она изменилась
                    updated = False
                    if username and user.username != username:
                        user.username = username
                        updated = True
                    if first_name and user.first_name != first_name:
                        user.first_name = first_name
                        updated = True
                    if last_name and user.last_name != last_name:
                        user.last_name = last_name
                        updated = True
                    
                    # Обновляем время последней активности
                    user.last_activity = datetime.utcnow()
                    
                    if updated or True:  # Всегда обновляем last_activity
                        await session.commit()
                        logger.info(f"Обновлена информация о пользователе {telegram_id}")
                    
                    return user

                else:
                    # Создаем нового пользователя
                    new_user = User(
                        telegram_id=telegram_id,
                        username=username,
                        first_name=first_name,
                        last_name=last_name,
                        created_at=datetime.utcnow(),
                        last_activity=datetime.utcnow(),
                        is_active=True
                    )
                    
                    session.add(new_user)
                    await session.commit()
                    await session.refresh(new_user)
                    
                    logger.info(f"Создан новый пользователь {telegram_id} ({first_name} {last_name})")
                    return new_user

            except Exception as e:
                logger.error(f"Ошибка при получении/создании пользователя {telegram_id}: {e}")
                await session.rollback()
                raise

    @staticmethod
    async def update_user_activity(telegram_id: int) -> bool:
        """
        Обновляет время последней активности пользователя
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            True если успешно обновлено
        """
        async with async_session() as session:
            try:
                query = update(User).where(User.telegram_id == telegram_id).values(
                    last_activity=datetime.utcnow()
                )
                result = await session.execute(query)
                await session.commit()
                
                return result.rowcount > 0

            except Exception as e:
                logger.error(f"Ошибка при обновлении активности пользователя {telegram_id}: {e}")
                await session.rollback()
                return False

    @staticmethod
    async def set_user_preferences(
        telegram_id: int,
        max_price: Optional[int] = None,
        min_price: Optional[int] = None,
        preferred_metro: Optional[list] = None
    ) -> bool:
        """
        Устанавливает предпочтения пользователя
        
        Args:
            telegram_id: ID пользователя в Telegram
            max_price: Максимальная цена
            min_price: Минимальная цена
            preferred_metro: Предпочитаемые станции метро
            
        Returns:
            True если успешно обновлено
        """
        async with async_session() as session:
            try:
                query = update(User).where(User.telegram_id == telegram_id)
                
                update_values = {}
                if max_price is not None:
                    update_values['max_price'] = max_price
                if min_price is not None:
                    update_values['min_price'] = min_price
                if preferred_metro is not None:
                    update_values['preferred_metro'] = preferred_metro
                
                if update_values:
                    query = query.values(**update_values)
                    result = await session.execute(query)
                    await session.commit()
                    
                    logger.info(f"Обновлены предпочтения пользователя {telegram_id}")
                    return result.rowcount > 0
                
                return True

            except Exception as e:
                logger.error(f"Ошибка при обновлении предпочтений пользователя {telegram_id}: {e}")
                await session.rollback()
                return False

    @staticmethod
    async def get_user_preferences(telegram_id: int) -> Optional[dict]:
        """
        Получает предпочтения пользователя
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            Словарь с предпочтениями или None
        """
        async with async_session() as session:
            try:
                query = select(User).where(User.telegram_id == telegram_id)
                result = await session.execute(query)
                user = result.scalar_one_or_none()

                if user:
                    return {
                        'max_price': user.max_price,
                        'min_price': user.min_price,
                        'preferred_metro': user.preferred_metro
                    }
                
                return None

            except Exception as e:
                logger.error(f"Ошибка при получении предпочтений пользователя {telegram_id}: {e}")
                return None

    @staticmethod
    async def deactivate_user(telegram_id: int) -> bool:
        """
        Деактивирует пользователя (не будет получать уведомления)
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            True если успешно деактивирован
        """
        async with async_session() as session:
            try:
                query = update(User).where(User.telegram_id == telegram_id).values(
                    is_active=False
                )
                result = await session.execute(query)
                await session.commit()
                
                logger.info(f"Пользователь {telegram_id} деактивирован")
                return result.rowcount > 0

            except Exception as e:
                logger.error(f"Ошибка при деактивации пользователя {telegram_id}: {e}")
                await session.rollback()
                return False

    @staticmethod
    async def activate_user(telegram_id: int) -> bool:
        """
        Активирует пользователя (будет получать уведомления)
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            True если успешно активирован
        """
        async with async_session() as session:
            try:
                query = update(User).where(User.telegram_id == telegram_id).values(
                    is_active=True
                )
                result = await session.execute(query)
                await session.commit()
                
                logger.info(f"Пользователь {telegram_id} активирован")
                return result.rowcount > 0

            except Exception as e:
                logger.error(f"Ошибка при активации пользователя {telegram_id}: {e}")
                await session.rollback()
                return False

    @staticmethod
    async def get_user_stats() -> dict:
        """
        Получает статистику по пользователям
        
        Returns:
            Словарь со статистикой
        """
        async with async_session() as session:
            try:
                from sqlalchemy import func
                
                # Общее количество пользователей
                total_query = select(func.count(User.id))
                total_result = await session.execute(total_query)
                total_users = total_result.scalar() or 0

                # Активные пользователи
                active_query = select(func.count(User.id)).where(User.is_active == True)
                active_result = await session.execute(active_query)
                active_users = active_result.scalar() or 0

                # Пользователи с настройками
                with_prefs_query = select(func.count(User.id)).where(
                    (User.max_price.is_not(None)) | 
                    (User.min_price.is_not(None)) |
                    (User.preferred_metro.is_not(None))
                )
                with_prefs_result = await session.execute(with_prefs_query)
                users_with_preferences = with_prefs_result.scalar() or 0

                return {
                    'total_users': total_users,
                    'active_users': active_users,
                    'inactive_users': total_users - active_users,
                    'users_with_preferences': users_with_preferences
                }

            except Exception as e:
                logger.error(f"Ошибка при получении статистики пользователей: {e}")
                return {
                    'total_users': 0,
                    'active_users': 0,
                    'inactive_users': 0,
                    'users_with_preferences': 0
                }