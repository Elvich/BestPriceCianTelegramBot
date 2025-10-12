"""
Сервис для работы с объявлениями о квартирах в базе данных.
Предоставляет высокоуровневые методы для сохранения и получения данных.
"""

import re
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.orm import selectinload
from datetime import datetime

from .models import async_session, Apartment, MetroStation, PriceHistory, User, FilterLog


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
        only_active: bool = True,
        only_production: bool = False
    ) -> List[Apartment]:
        """
        Получает список объявлений с фильтрацией
        
        Args:
            limit: Максимальное количество результатов
            min_price: Минимальная цена
            max_price: Максимальная цена
            metro_stations: Список предпочитаемых станций метро
            only_active: Показывать только активные объявления
            only_production: Показывать только квартиры из production (прошедшие фильтрацию)
            
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
            
            if only_production:
                conditions.append(Apartment.is_staging == False)
            
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
    async def calculate_weighted_average_price(
        rooms: Optional[int] = None,
        metro_station: Optional[str] = None,
        district: Optional[str] = None,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Вычисляет средневзвешенную цену квартир по параметрам
        
        Args:
            rooms: Количество комнат (None = все)
            metro_station: Станция метро (None = все)
            district: Район (None = все)  
            days_back: За сколько дней учитывать данные
            
        Returns:
            Dict с метриками: average_price, median_price, count, price_per_sqm
        """
        from sqlalchemy import func, and_
        from datetime import datetime, timedelta
        
        async with async_session() as session:
            # Базовые условия - только production активные квартиры
            conditions = [
                Apartment.is_staging == False,
                Apartment.is_active == True,
                Apartment.price.isnot(None),
                Apartment.first_seen >= datetime.utcnow() - timedelta(days=days_back)
            ]
            
            # Дополнительные фильтры
            if rooms is not None:
                conditions.append(Apartment.rooms == rooms)
                
            # Если указана станция метро, нужно джойнить с MetroStation
            query = select(Apartment)
            
            if metro_station:
                from .models import MetroStation
                query = query.join(MetroStation).where(
                    MetroStation.station_name.ilike(f"%{metro_station}%")
                )
            
            if district:
                conditions.append(Apartment.address.ilike(f"%{district}%"))
            
            # Применяем все условия
            query = query.where(and_(*conditions))
            
            result = await session.execute(query)
            apartments = result.scalars().all()
            
            if not apartments:
                return {
                    'average_price': None,
                    'median_price': None,
                    'average_price_per_sqm': None,
                    'count': 0,
                    'rooms': rooms,
                    'metro_station': metro_station,
                    'district': district
                }
            
            # Вычисляем метрики
            prices = [apt.price for apt in apartments if apt.price]
            prices_per_sqm = [apt.price_per_sqm for apt in apartments if apt.price_per_sqm]
            
            average_price = sum(prices) / len(prices) if prices else None
            median_price = sorted(prices)[len(prices)//2] if prices else None
            average_price_per_sqm = sum(prices_per_sqm) / len(prices_per_sqm) if prices_per_sqm else None
            
            return {
                'average_price': round(average_price) if average_price else None,
                'median_price': round(median_price) if median_price else None,
                'average_price_per_sqm': round(average_price_per_sqm) if average_price_per_sqm else None,
                'count': len(apartments),
                'rooms': rooms,
                'metro_station': metro_station,
                'district': district,
                'days_analyzed': days_back
            }
    
    @staticmethod
    async def calculate_staging_average_price(
        rooms: Optional[int] = None,
        metro_station: Optional[str] = None,
        exclude_cian_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Вычисляет средневзвешенную цену среди НОВЫХ (staging) квартир
        
        Args:
            rooms: Количество комнат (None = все)
            metro_station: Станция метро (None = все)
            exclude_cian_id: Исключить квартиру из расчета (саму тестируемую)
            
        Returns:
            Dict с метриками: average_price, median_price, count, price_per_sqm
        """
        from sqlalchemy import func, and_
        
        async with async_session() as session:
            # Базовые условия - только staging активные квартиры с ценами
            conditions = [
                Apartment.is_staging == True,
                Apartment.is_active == True,
                Apartment.price.isnot(None),
                Apartment.filter_status == 'pending'  # Только необработанные
            ]
            
            # Исключаем саму тестируемую квартиру из расчета
            if exclude_cian_id:
                conditions.append(Apartment.cian_id != exclude_cian_id)
            
            # Дополнительные фильтры
            if rooms is not None:
                conditions.append(Apartment.rooms == rooms)
                
            # Если указана станция метро, нужно джойнить с MetroStation
            query = select(Apartment)
            
            if metro_station:
                from .models import MetroStation
                query = query.join(MetroStation).where(
                    MetroStation.station_name.ilike(f"%{metro_station}%")
                )
            
            # Применяем все условия
            query = query.where(and_(*conditions))
            
            result = await session.execute(query)
            apartments = result.scalars().all()
            
            if not apartments:
                return {
                    'average_price': None,
                    'median_price': None,
                    'average_price_per_sqm': None,
                    'count': 0,
                    'rooms': rooms,
                    'metro_station': metro_station
                }
            
            # Вычисляем метрики
            prices = [apt.price for apt in apartments if apt.price]
            prices_per_sqm = [apt.price_per_sqm for apt in apartments if apt.price_per_sqm]
            
            average_price = sum(prices) / len(prices) if prices else None
            median_price = sorted(prices)[len(prices)//2] if prices else None
            average_price_per_sqm = sum(prices_per_sqm) / len(prices_per_sqm) if prices_per_sqm else None
            
            return {
                'average_price': round(average_price) if average_price else None,
                'median_price': round(median_price) if median_price else None,
                'average_price_per_sqm': round(average_price_per_sqm) if average_price_per_sqm else None,
                'count': len(apartments),
                'rooms': rooms,
                'metro_station': metro_station
            }
    
    @staticmethod
    async def get_market_benchmark(apartment: Apartment) -> Dict[str, Any]:
        """
        Получает рыночный бенчмарк для конкретной квартиры
        
        Args:
            apartment: Квартира для анализа
            
        Returns:
            Dict с рыночными метриками и процентом отклонения
        """
        # Сначала пытаемся найти похожие НОВЫЕ квартиры по станции метро
        benchmark = None
        metro_station = None
        
        if apartment.metro_stations:
            metro_station = apartment.metro_stations[0].station_name
            benchmark = await ApartmentService.calculate_staging_average_price(
                rooms=apartment.rooms,
                metro_station=metro_station,
                exclude_cian_id=apartment.cian_id
            )
        
        # Если по метро мало данных, берем общую статистику по количеству комнат среди НОВЫХ
        if not benchmark or benchmark['count'] < 2:
            benchmark = await ApartmentService.calculate_staging_average_price(
                rooms=apartment.rooms,
                exclude_cian_id=apartment.cian_id
            )
            metro_station = None
        
        # Если и этого мало, берем вообще всю статистику НОВЫХ квартир
        if not benchmark or benchmark['count'] < 2:
            benchmark = await ApartmentService.calculate_staging_average_price(
                exclude_cian_id=apartment.cian_id
            )
            
        # Вычисляем отклонение от рынка
        price_deviation = None
        price_per_sqm_deviation = None
        
        if benchmark['average_price'] and apartment.price:
            price_deviation = ((apartment.price - benchmark['average_price']) / benchmark['average_price']) * 100
            
        if benchmark['average_price_per_sqm'] and apartment.price_per_sqm:
            price_per_sqm_deviation = ((apartment.price_per_sqm - benchmark['average_price_per_sqm']) / benchmark['average_price_per_sqm']) * 100
        
        return {
            'benchmark': benchmark,
            'comparison_type': 'new_metro' if metro_station else 'new_rooms' if apartment.rooms else 'new_general',
            'price_deviation_percent': round(price_deviation, 1) if price_deviation is not None else None,
            'price_per_sqm_deviation_percent': round(price_per_sqm_deviation, 1) if price_per_sqm_deviation is not None else None,
            'is_below_market': price_deviation < 0 if price_deviation is not None else None
        }
    
    @staticmethod
    async def get_statistics(staging_only: bool = False) -> Dict[str, Any]:
        """Получает статистику по объявлениям"""
        async with async_session() as session:
            # Базовый фильтр для staging или production
            base_condition = Apartment.is_staging == staging_only
            
            if staging_only:
                # Статистика для staging
                total_query = select(Apartment).where(base_condition)
                total_result = await session.execute(total_query)
                total_count = len(total_result.scalars().all())
                
                # Pending объявления
                pending_query = select(Apartment).where(
                    and_(base_condition, Apartment.filter_status == 'pending')
                )
                pending_result = await session.execute(pending_query)
                pending_count = len(pending_result.scalars().all())
                
                # Одобренные объявления
                approved_query = select(Apartment).where(
                    and_(base_condition, Apartment.filter_status == 'approved')
                )
                approved_result = await session.execute(approved_query)
                approved_count = len(approved_result.scalars().all())
                
                # Отклоненные объявления
                rejected_query = select(Apartment).where(
                    and_(base_condition, Apartment.filter_status == 'rejected')
                )
                rejected_result = await session.execute(rejected_query)
                rejected_count = len(rejected_result.scalars().all())
                
                return {
                    'total_apartments': total_count,
                    'pending_apartments': pending_count,
                    'approved_apartments': approved_count,
                    'rejected_apartments': rejected_count,
                    'processed_apartments': approved_count + rejected_count
                }
            else:
                # Статистика для production (старая логика)
                total_query = select(Apartment).where(base_condition)
                total_result = await session.execute(total_query)
                total_count = len(total_result.scalars().all())
                
                # Активные объявления
                active_query = select(Apartment).where(
                    and_(base_condition, Apartment.is_active == True)
                )
                active_result = await session.execute(active_query)
                active_count = len(active_result.scalars().all())
                
                # Средняя цена активных объявлений
                from sqlalchemy import func
                avg_price_query = select(func.avg(Apartment.price)).where(
                    and_(base_condition, Apartment.is_active == True, Apartment.price.isnot(None))
                )
                avg_price_result = await session.execute(avg_price_query)
                avg_price = avg_price_result.scalar()
                
                return {
                    'total_apartments': total_count,
                    'active_apartments': active_count,
                    'inactive_apartments': total_count - active_count,
                    'average_price': int(avg_price) if avg_price else 0
                }
    
    @staticmethod
    async def save_to_staging(apartments_data: List[List[Any]]) -> Dict[str, int]:
        """
        Сохраняет данные парсера в staging (is_staging=True)
        
        Args:
            apartments_data: Список данных в формате [url, title, price, price_per_sqm, details]
            
        Returns:
            Dict с статистикой: {'created': int, 'updated': int, 'errors': int}
        """
        stats = {'created': 0, 'updated': 0, 'errors': 0}
        
        for apartment_data in apartments_data:
            async with async_session() as session:
                try:
                    url, title, price_str, price_per_sqm_str = apartment_data[:4]
                    details = apartment_data[4] if len(apartment_data) > 4 else None
                    
                    # Извлекаем ID объявления
                    cian_id = ApartmentService.extract_cian_id(url)
                    
                    # Парсим цены
                    price = ApartmentService.parse_price(price_str)
                    price_per_sqm = ApartmentService.parse_price(price_per_sqm_str)
                    
                    # Проверяем существование в staging
                    existing_query = select(Apartment).where(
                        and_(Apartment.cian_id == cian_id, Apartment.is_staging == True)
                    )
                    existing_result = await session.execute(existing_query)
                    existing = existing_result.scalar_one_or_none()
                    
                    if existing and existing.filter_status == 'pending':
                        # Обновляем только необработанные записи
                        existing.title = title
                        existing.price = price
                        existing.price_per_sqm = price_per_sqm
                        existing.last_updated = datetime.utcnow()
                        
                        # Обновляем детали если есть
                        if details and isinstance(details, dict):
                            existing.address = details.get('address')
                            
                            # Удаляем старые станции метро и добавляем новые
                            for metro in existing.metro_stations:
                                await session.delete(metro)
                            
                            metro_stations = details.get('metro_stations', [])
                            for metro_info in metro_stations:
                                if isinstance(metro_info, dict):
                                    metro_station = MetroStation(
                                        station_name=metro_info.get('station', ''),
                                        travel_time=metro_info.get('time', '')
                                    )
                                    existing.metro_stations.append(metro_station)
                        
                        stats['updated'] += 1
                        
                    elif not existing:
                        # Создаем новую запись в staging
                        apartment = Apartment(
                            cian_id=cian_id,
                            url=url,
                            title=title,
                            price=price,
                            price_per_sqm=price_per_sqm,
                            is_staging=True,
                            filter_status='pending'
                        )
                        
                        # Обрабатываем детали
                        if details and isinstance(details, dict):
                            apartment.address = details.get('address')
                            
                            metro_stations = details.get('metro_stations', [])
                            for metro_info in metro_stations:
                                if isinstance(metro_info, dict):
                                    metro_station = MetroStation(
                                        station_name=metro_info.get('station', ''),
                                        travel_time=metro_info.get('time', '')
                                    )
                                    apartment.metro_stations.append(metro_station)
                        
                        session.add(apartment)
                        stats['created'] += 1
                    
                    await session.commit()
                        
                except Exception as e:
                    print(f"Ошибка при сохранении в staging: {url} - {e}")
                    await session.rollback()
                    stats['errors'] += 1
                    continue
        
        return stats
    
    @staticmethod
    async def get_pending_apartments(limit: int = 100) -> List[Apartment]:
        """Получает список необработанных квартир для фильтрации"""
        async with async_session() as session:
            query = select(Apartment).options(
                selectinload(Apartment.metro_stations)
            ).where(
                and_(Apartment.is_staging == True, Apartment.filter_status == 'pending')
            ).order_by(Apartment.first_seen.desc()).limit(limit)
            
            result = await session.execute(query)
            return result.scalars().all()
    
    @staticmethod
    async def mark_apartment_processed(
        cian_id: str, 
        status: str, 
        reason: Optional[str] = None
    ) -> bool:
        """Помечает квартиру как обработанную"""
        async with async_session() as session:
            try:
                from sqlalchemy import update
                query = update(Apartment).where(
                    and_(Apartment.cian_id == cian_id, Apartment.is_staging == True)
                ).values(
                    filter_status=status,
                    filter_reason=reason,
                    processed_at=datetime.utcnow()
                )
                
                result = await session.execute(query)
                await session.commit()
                
                return result.rowcount > 0
                
            except Exception as e:
                print(f"Ошибка при обновлении статуса: {e}")
                await session.rollback()
                return False
    
    @staticmethod
    async def move_to_production(staging_apartment: Apartment):
        """Перемещает одобренную квартиру в production (is_staging=False)"""
        async with async_session() as session:
            try:
                # Просто переключаем статус staging квартиры в production
                staging_apartment.is_staging = False
                staging_apartment.is_active = True
                staging_apartment.last_updated = datetime.utcnow()
                
                # Мержим изменения в текущую сессию
                merged_apartment = await session.merge(staging_apartment)
                await session.commit()
                
            except Exception as e:
                print(f"Ошибка при перемещении в production: {e}")
                await session.rollback()
                raise
    
    @staticmethod
    async def log_filter_result(
        cian_id: str,
        filter_name: str,
        result: str,
        reason: Optional[str] = None
    ):
        """Логирует результат работы фильтра"""
        async with async_session() as session:
            try:
                log_entry = FilterLog(
                    apartment_cian_id=cian_id,
                    filter_name=filter_name,
                    result=result,
                    reason=reason
                )
                session.add(log_entry)
                await session.commit()
                
            except Exception as e:
                print(f"Ошибка при логировании фильтра: {e}")
                await session.rollback()
    
    @staticmethod
    async def get_metro_stations(apartment_id: int) -> List[MetroStation]:
        """
        Получает список станций метро для квартиры
        
        Args:
            apartment_id: ID квартиры
            
        Returns:
            Список объектов MetroStation
        """
        async with async_session() as session:
            try:
                result = await session.execute(
                    select(MetroStation).where(MetroStation.apartment_id == apartment_id)
                )
                return result.scalars().all()
            except Exception as e:
                print(f"Ошибка при получении данных о метро: {e}")
                return []