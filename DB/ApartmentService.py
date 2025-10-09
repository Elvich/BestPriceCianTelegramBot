"""
Сервис для работы с объявлениями о квартирах в базе данных.
Предоставляет высокоуровневые методы для сохранения и получения данных.
"""

import re
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.orm import selectinload
from datetime import datetime

from .Models import async_session, Apartment, MetroStation, PriceHistory, User


class ApartmentService:
    """Сервис для работы с объявлениями о квартирах"""
    
    @staticmethod
    def extract_cian_id(url: str) -> str:
        """Извлекает ID объявления из URL Cian"""
        # Паттерн для извлечения ID из URL вида: https://www.cian.ru/sale/flat/123456789/
        match = re.search(r'/(\d+)/?$', url)
        if match:
            return match.group(1)
        # Fallback - используем хеш от URL
        return str(hash(url))
    
    @staticmethod
    def parse_price(price_str: str) -> Optional[int]:
        """Извлекает числовое значение цены из строки"""
        if not price_str:
            return None
        # Убираем все символы кроме цифр
        digits = re.sub(r'[^\d]', '', price_str)
        return int(digits) if digits else None
    
    @staticmethod
    async def save_apartments(apartments_data: List[List[Any]]) -> Dict[str, int]:
        """
        Сохраняет список объявлений в базу данных
        
        Args:
            apartments_data: Список данных в формате [url, title, price, price_per_sqm, details]
            
        Returns:
            Dict с статистикой: {'created': int, 'updated': int, 'errors': int}
        """
        stats = {'created': 0, 'updated': 0, 'errors': 0}
        
        for apartment_data in apartments_data:
            # Каждое объявление обрабатываем в отдельной транзакции
            async with async_session() as session:
                try:
                    url, title, price_str, price_per_sqm_str = apartment_data[:4]
                    details = apartment_data[4] if len(apartment_data) > 4 else None
                    
                    # Извлекаем ID объявления
                    cian_id = ApartmentService.extract_cian_id(url)
                    
                    # Парсим цены
                    price = ApartmentService.parse_price(price_str)
                    price_per_sqm = ApartmentService.parse_price(price_per_sqm_str)
                    
                    # Проверяем, существует ли объявление по cian_id
                    from sqlalchemy import select
                    existing_query = select(Apartment).where(Apartment.cian_id == cian_id)
                    existing_result = await session.execute(existing_query)
                    existing = existing_result.scalar_one_or_none()
                    
                    if existing:
                        # Обновляем существующее объявление
                        price_changed = existing.price != price
                        
                        existing.title = title
                        existing.price = price
                        existing.price_per_sqm = price_per_sqm
                        existing.last_updated = datetime.utcnow()
                        existing.is_active = True
                        
                        # Если цена изменилась, записываем в историю
                        if price_changed and price:
                            price_record = PriceHistory(
                                apartment_id=existing.id,
                                price=price,
                                price_per_sqm=price_per_sqm
                            )
                            session.add(price_record)
                        
                        stats['updated'] += 1
                    else:
                        # Создаем новое объявление
                        apartment = Apartment(
                            cian_id=cian_id,
                            url=url,
                            title=title,
                            price=price,
                            price_per_sqm=price_per_sqm
                        )
                        
                        # Обрабатываем детали из глубокого парсинга
                        if details and isinstance(details, dict):
                            apartment.address = details.get('address')
                            
                            # Сохраняем станции метро
                            metro_stations = details.get('metro_stations', [])
                            for metro_info in metro_stations:
                                if isinstance(metro_info, dict):
                                    metro_station = MetroStation(
                                        station_name=metro_info.get('station', ''),
                                        travel_time=metro_info.get('time', '')
                                    )
                                    apartment.metro_stations.append(metro_station)
                        
                        session.add(apartment)
                        
                        # Добавляем первую запись в историю цен
                        if price:
                            # Нужно сначала сохранить apartment, чтобы получить id
                            await session.flush()
                            price_record = PriceHistory(
                                apartment_id=apartment.id,
                                price=price,
                                price_per_sqm=price_per_sqm
                            )
                            session.add(price_record)
                        
                        stats['created'] += 1
                    
                    # Коммитим транзакцию для текущего объявления
                    await session.commit()
                        
                except Exception as e:
                    print(f"Ошибка при сохранении объявления {url}: {e}")
                    await session.rollback()
                    stats['errors'] += 1
                    continue
        
        return stats
    
    @staticmethod
    async def get_apartments(
        limit: int = 100,
        min_price: Optional[int] = None,
        max_price: Optional[int] = None,
        metro_stations: Optional[List[str]] = None,
        only_active: bool = True
    ) -> List[Apartment]:
        """
        Получает список объявлений с фильтрацией
        
        Args:
            limit: Максимальное количество результатов
            min_price: Минимальная цена
            max_price: Максимальная цена
            metro_stations: Список предпочитаемых станций метро
            only_active: Показывать только активные объявления
            
        Returns:
            Список объявлений
        """
        async with async_session() as session:
            query = select(Apartment).options(
                selectinload(Apartment.metro_stations),
                selectinload(Apartment.price_history)
            )
            
            # Применяем фильтры
            conditions = []
            
            if only_active:
                conditions.append(Apartment.is_active == True)
            
            if min_price:
                conditions.append(Apartment.price >= min_price)
            
            if max_price:
                conditions.append(Apartment.price <= max_price)
            
            if metro_stations:
                # Ищем объявления рядом с указанными станциями метро
                metro_condition = select(MetroStation.apartment_id).where(
                    MetroStation.station_name.in_(metro_stations)
                )
                conditions.append(Apartment.id.in_(metro_condition))
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Сортируем по цене (сначала самые дешевые)
            query = query.order_by(Apartment.price.asc()).limit(limit)
            
            result = await session.execute(query)
            return result.scalars().all()
    
    @staticmethod
    async def get_price_drops(days: int = 7, min_drop_percent: float = 5.0) -> List[Apartment]:
        """
        Находит объявления со значительным снижением цены
        
        Args:
            days: За сколько дней искать изменения
            min_drop_percent: Минимальный процент снижения цены
            
        Returns:
            Список объявлений со снижением цены
        """
        # Реализация поиска снижения цен
        # Это более сложный запрос, который требует анализа истории цен
        pass
    
    @staticmethod
    async def mark_as_inactive(cian_ids: List[str]) -> int:
        """
        Помечает объявления как неактивные (если они исчезли с сайта)
        
        Args:
            cian_ids: Список ID объявлений, которые все еще активны
            
        Returns:
            Количество помеченных как неактивные
        """
        async with async_session() as session:
            # Помечаем как неактивные все объявления, которых нет в списке
            query = select(Apartment).where(
                and_(
                    Apartment.is_active == True,
                    ~Apartment.cian_id.in_(cian_ids)
                )
            )
            
            result = await session.execute(query)
            apartments_to_deactivate = result.scalars().all()
            
            for apartment in apartments_to_deactivate:
                apartment.is_active = False
                apartment.last_updated = datetime.utcnow()
            
            await session.commit()
            
            return len(apartments_to_deactivate)
    
    @staticmethod
    async def get_statistics() -> Dict[str, Any]:
        """Получает статистику по объявлениям"""
        async with async_session() as session:
            # Общее количество объявлений
            total_query = select(Apartment)
            total_result = await session.execute(total_query)
            total_count = len(total_result.scalars().all())
            
            # Активные объявления
            active_query = select(Apartment).where(Apartment.is_active == True)
            active_result = await session.execute(active_query)
            active_count = len(active_result.scalars().all())
            
            # Средняя цена активных объявлений
            from sqlalchemy import func
            avg_price_query = select(func.avg(Apartment.price)).where(
                and_(Apartment.is_active == True, Apartment.price.isnot(None))
            )
            avg_price_result = await session.execute(avg_price_query)
            avg_price = avg_price_result.scalar()
            
            return {
                'total_apartments': total_count,
                'active_apartments': active_count,
                'inactive_apartments': total_count - active_count,
                'average_price': int(avg_price) if avg_price else 0
            }