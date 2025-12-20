"""
Сервис для управления реакциями пользователей на квартиры.
Обрабатывает лайки и дизлайки.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, delete
from sqlalchemy.orm import selectinload

from .models import async_session, UserApartmentReaction, Apartment, User

logger = logging.getLogger(__name__)


class ReactionService:
    """Сервис для управления лайками и дизлайками пользователей"""

    @staticmethod
    async def toggle_reaction(telegram_id: int, apartment_id: int, reaction: str) -> Dict[str, Any]:
        """
        Переключает реакцию пользователя на квартиру.
        Если реакция уже есть - удаляет её.
        Если другая реакция - заменяет на новую.
        
        Args:
            telegram_id: ID пользователя в Telegram
            apartment_id: ID квартиры
            reaction: 'like' или 'dislike'
            
        Returns:
            Dict с информацией о действии: {'action': 'added'/'removed'/'changed', 'reaction': str}
        """
        if reaction not in ['like', 'dislike']:
            raise ValueError("Реакция должна быть 'like' или 'dislike'")

        async with async_session() as session:
            # Проверяем существующую реакцию
            query = select(UserApartmentReaction).where(
                and_(
                    UserApartmentReaction.telegram_id == telegram_id,
                    UserApartmentReaction.apartment_id == apartment_id
                )
            )
            result = await session.execute(query)
            existing_reaction = result.scalar_one_or_none()

            if existing_reaction:
                if existing_reaction.reaction == reaction:
                    # Удаляем существующую реакцию (toggle off)
                    await session.delete(existing_reaction)
                    await session.commit()
                    logger.info(f"Пользователь {telegram_id} удалил {reaction} с квартиры {apartment_id}")
                    return {'action': 'removed', 'reaction': reaction}
                else:
                    # Изменяем реакцию
                    existing_reaction.reaction = reaction
                    existing_reaction.updated_at = datetime.utcnow()
                    await session.commit()
                    logger.info(f"Пользователь {telegram_id} изменил реакцию на {reaction} для квартиры {apartment_id}")
                    return {'action': 'changed', 'reaction': reaction, 'previous': existing_reaction.reaction}
            else:
                # Добавляем новую реакцию
                new_reaction = UserApartmentReaction(
                    telegram_id=telegram_id,
                    apartment_id=apartment_id,
                    reaction=reaction
                )
                session.add(new_reaction)
                await session.commit()
                logger.info(f"Пользователь {telegram_id} поставил {reaction} квартире {apartment_id}")
                return {'action': 'added', 'reaction': reaction}

    @staticmethod
    async def get_user_reaction(telegram_id: int, apartment_id: int) -> Optional[str]:
        """
        Получает текущую реакцию пользователя на квартиру
        
        Args:
            telegram_id: ID пользователя в Telegram
            apartment_id: ID квартиры
            
        Returns:
            'like', 'dislike' или None
        """
        async with async_session() as session:
            query = select(UserApartmentReaction).where(
                and_(
                    UserApartmentReaction.telegram_id == telegram_id,
                    UserApartmentReaction.apartment_id == apartment_id
                )
            )
            result = await session.execute(query)
            reaction = result.scalar_one_or_none()
            return reaction.reaction if reaction else None

    @staticmethod
    async def get_user_liked_apartments(telegram_id: int, limit: int = 50) -> List[Apartment]:
        """
        Получает список квартир, которые пользователь лайкнул
        
        Args:
            telegram_id: ID пользователя в Telegram
            limit: Максимальное количество результатов
            
        Returns:
            Список квартир с лайками
        """
        async with async_session() as session:
            query = (
                select(Apartment)
                .join(UserApartmentReaction)
                .where(
                    and_(
                        UserApartmentReaction.telegram_id == telegram_id,
                        UserApartmentReaction.reaction == 'like',
                        Apartment.is_active == True
                    )
                )
                .options(selectinload(Apartment.metro_stations))
                .order_by(UserApartmentReaction.updated_at.desc())
                .limit(limit)
            )
            result = await session.execute(query)
            return list(result.scalars().all())

    @staticmethod
    async def get_user_disliked_apartments(telegram_id: int, limit: int = 50) -> List[Apartment]:
        """
        Получает список квартир, которые пользователь дизлайкнул
        
        Args:
            telegram_id: ID пользователя в Telegram
            limit: Максимальное количество результатов
            
        Returns:
            Список квартир с дизлайками
        """
        async with async_session() as session:
            query = (
                select(Apartment)
                .join(UserApartmentReaction)
                .where(
                    and_(
                        UserApartmentReaction.telegram_id == telegram_id,
                        UserApartmentReaction.reaction == 'dislike',
                        Apartment.is_active == True
                    )
                )
                .options(selectinload(Apartment.metro_stations))
                .order_by(UserApartmentReaction.updated_at.desc())
                .limit(limit)
            )
            result = await session.execute(query)
            return list(result.scalars().all())

    @staticmethod
    async def get_user_reactions_summary(telegram_id: int) -> Dict[str, int]:
        """
        Получает сводку по реакциям пользователя
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            Словарь с количеством лайков и дизлайков
        """
        async with async_session() as session:
            # Считаем лайки
            likes_query = select(UserApartmentReaction).where(
                and_(
                    UserApartmentReaction.telegram_id == telegram_id,
                    UserApartmentReaction.reaction == 'like'
                )
            )
            likes_result = await session.execute(likes_query)
            likes_count = len(list(likes_result.scalars().all()))

            # Считаем дизлайки
            dislikes_query = select(UserApartmentReaction).where(
                and_(
                    UserApartmentReaction.telegram_id == telegram_id,
                    UserApartmentReaction.reaction == 'dislike'
                )
            )
            dislikes_result = await session.execute(dislikes_query)
            dislikes_count = len(list(dislikes_result.scalars().all()))

            return {
                'likes': likes_count,
                'dislikes': dislikes_count,
                'total': likes_count + dislikes_count
            }

    @staticmethod
    async def get_disliked_apartment_ids(telegram_id: int) -> List[int]:
        """
        Получает список ID дизлайкнутых квартир для исключения из поиска
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            Список ID квартир с дизлайками
        """
        async with async_session() as session:
            query = select(UserApartmentReaction.apartment_id).where(
                and_(
                    UserApartmentReaction.telegram_id == telegram_id,
                    UserApartmentReaction.reaction == 'dislike'
                )
            )
            result = await session.execute(query)
            return list(result.scalars().all())

    @staticmethod
    async def remove_reaction(telegram_id: int, apartment_id: int) -> bool:
        """
        Удаляет реакцию пользователя на квартиру
        
        Args:
            telegram_id: ID пользователя в Telegram
            apartment_id: ID квартиры
            
        Returns:
            True если реакция была удалена, False если её не было
        """
        async with async_session() as session:
            query = delete(UserApartmentReaction).where(
                and_(
                    UserApartmentReaction.telegram_id == telegram_id,
                    UserApartmentReaction.apartment_id == apartment_id
                )
            )
            result = await session.execute(query)
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    async def get_apartment_reactions_stats(apartment_id: int) -> Dict[str, int]:
        """
        Получает статистику реакций для конкретной квартиры
        
        Args:
            apartment_id: ID квартиры
            
        Returns:
            Словарь с количеством лайков и дизлайков
        """
        async with async_session() as session:
            # Считаем лайки
            likes_query = select(UserApartmentReaction).where(
                and_(
                    UserApartmentReaction.apartment_id == apartment_id,
                    UserApartmentReaction.reaction == 'like'
                )
            )
            likes_result = await session.execute(likes_query)
            likes_count = len(list(likes_result.scalars().all()))

            # Считаем дизлайки
            dislikes_query = select(UserApartmentReaction).where(
                and_(
                    UserApartmentReaction.apartment_id == apartment_id,
                    UserApartmentReaction.reaction == 'dislike'
                )
            )
            dislikes_result = await session.execute(dislikes_query)
            dislikes_count = len(list(dislikes_result.scalars().all()))

            return {
                'likes': likes_count,
                'dislikes': dislikes_count,
                'total': likes_count + dislikes_count
            }