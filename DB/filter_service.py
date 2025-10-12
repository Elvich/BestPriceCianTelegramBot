"""
Сервис фильтрации квартир.
Проверяет квартиры из staging БД на соответствие условиям и перемещает подходящие в основную БД.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from .apartment_service import ApartmentService
from .models import Apartment


@dataclass
class FilterConfig:
    """Конфигурация фильтров"""
    # Ценовые фильтры
    max_price: Optional[int] = None
    min_price: Optional[int] = None
    max_price_per_sqm: Optional[int] = None
    min_price_per_sqm: Optional[int] = None
    
    # Рыночные фильтры
    min_market_discount_percent: float = 10.0  # минимальная скидка относительно рынка в %
    enable_market_filter: bool = True  # включить фильтр по рыночным ценам
    
    # Географические фильтры
    allowed_metro_stations: Optional[List[str]] = None
    blocked_metro_stations: Optional[List[str]] = None
    required_metro_distance: Optional[int] = None  # максимальное время до метро в минутах
    
    # Фильтры по характеристикам
    min_area: Optional[float] = None
    max_area: Optional[float] = None
    allowed_rooms: Optional[List[int]] = None
    min_floor: Optional[int] = None
    max_floor: Optional[int] = None
    
    # Качественные фильтры
    blocked_keywords: Optional[List[str]] = None  # слова в заголовке, которые исключают объявление
    required_keywords: Optional[List[str]] = None  # обязательные слова
    
    # Фильтры дубликатов и качества
    check_duplicates: bool = True
    min_title_length: int = 10


class BaseFilter(ABC):
    """Базовый класс для фильтров"""
    
    def __init__(self, config: FilterConfig):
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    async def check(self, apartment: Apartment) -> Dict[str, Any]:
        """
        Проверяет квартиру на соответствие условиям
        
        Returns:
            Dict с ключами: 'passed' (bool), 'reason' (str)
        """
        pass


class PriceFilter(BaseFilter):
    """Фильтр по цене"""
    
    async def check(self, apartment: Apartment) -> Dict[str, Any]:
        if not apartment.price:
            return {'passed': False, 'reason': 'Цена не указана'}
        
        if self.config.min_price and apartment.price < self.config.min_price:
            return {'passed': False, 'reason': f'Цена слишком низкая: {apartment.price:,}'}
        
        if self.config.max_price and apartment.price > self.config.max_price:
            return {'passed': False, 'reason': f'Цена слишком высокая: {apartment.price:,}'}
        
        if apartment.price_per_sqm:
            if self.config.min_price_per_sqm and apartment.price_per_sqm < self.config.min_price_per_sqm:
                return {'passed': False, 'reason': f'Цена за м² слишком низкая: {apartment.price_per_sqm:,}'}
            
            if self.config.max_price_per_sqm and apartment.price_per_sqm > self.config.max_price_per_sqm:
                return {'passed': False, 'reason': f'Цена за м² слишком высокая: {apartment.price_per_sqm:,}'}
        
        return {'passed': True, 'reason': 'Цена соответствует критериям'}


class MetroFilter(BaseFilter):
    """Фильтр по станциям метро"""
    
    def __init__(self, config: FilterConfig):
        super().__init__(config)
        # Загружаем конфигурацию станций из внешнего файла
        try:
            from config.metro_config import get_blocked_stations, get_preferred_stations, MAX_METRO_DISTANCE_MINUTES
            self.blocked_stations = get_blocked_stations()
            self.preferred_stations = get_preferred_stations()
            self.default_max_distance = MAX_METRO_DISTANCE_MINUTES
        except ImportError:
            # Fallback на старую конфигурацию если файл не найден
            self.blocked_stations = config.blocked_metro_stations or []
            self.preferred_stations = []
            self.default_max_distance = 10
    
    async def check(self, apartment: Apartment) -> Dict[str, Any]:
        if not apartment.metro_stations:
            # Если не требуется проверка расстояния до метро, пропускаем
            if not self.config.required_metro_distance and not self.config.allowed_metro_stations and not self.config.blocked_metro_stations:
                return {'passed': True, 'reason': 'Проверка метро не требуется'}
            return {'passed': False, 'reason': 'Нет информации о метро'}
        
        # Фильтруем станции метро, исключая заблокированные
        valid_stations = []
        blocked_stations_found = []
        preferred_stations_found = []
        
        for metro in apartment.metro_stations:
            station_name = metro.station_name
            
            # Проверяем, есть ли станция в бан-листе
            is_blocked = False
            for blocked in self.blocked_stations:
                if blocked.lower() in station_name.lower() or station_name.lower() in blocked.lower():
                    is_blocked = True
                    blocked_stations_found.append(station_name)
                    break
            
            # Добавляем станцию в список валидных, если она не заблокирована
            if not is_blocked:
                valid_stations.append(metro)
                
                # Проверяем, является ли станция предпочитаемой
                for preferred in self.preferred_stations:
                    if preferred.lower() in station_name.lower() or station_name.lower() in preferred.lower():
                        preferred_stations_found.append(station_name)
                        break
        
        # Если все станции заблокированы
        if not valid_stations:
            if blocked_stations_found:
                return {'passed': False, 'reason': f'Все станции в бан-листе: {", ".join(blocked_stations_found)}'}
            else:
                return {'passed': False, 'reason': 'Нет валидных станций метро'}
        
        # Проверяем разрешенные станции (если указаны)
        if self.config.allowed_metro_stations:
            has_allowed = False
            for metro in valid_stations:
                if any(allowed.lower() in metro.station_name.lower() or metro.station_name.lower() in allowed.lower() 
                       for allowed in self.config.allowed_metro_stations):
                    has_allowed = True
                    break
            
            if not has_allowed:
                station_names = [metro.station_name for metro in valid_stations]
                return {'passed': False, 'reason': f'Нет разрешенных станций среди валидных: {", ".join(station_names)}'}
        
        # Находим ближайшую станцию среди валидных
        closest_station = None
        closest_minutes = float('inf')
        
        import re
        for metro in valid_stations:
            if metro.travel_time:
                # Извлекаем число минут из строки типа "8 мин пешком", "10 мин на транспорте"
                time_match = re.search(r'(\d+)', metro.travel_time)
                if time_match:
                    minutes = int(time_match.group(1))
                    if minutes < closest_minutes:
                        closest_minutes = minutes
                        closest_station = metro
        
        # Проверяем время до ближайшей валидной станции
        max_distance = getattr(self.config, 'required_metro_distance', self.default_max_distance)
        
        if closest_station is None:
            return {'passed': False, 'reason': 'Нет информации о времени до станций метро'}
        
        if closest_minutes <= max_distance:
            # Формируем информативное сообщение
            status_parts = [f'Ближайшая станция {closest_station.station_name} в {closest_minutes} мин']
            
            if preferred_stations_found:
                status_parts.append(f"(⭐ предпочитаемые: {', '.join(preferred_stations_found)})")
            
            if blocked_stations_found:
                status_parts.append(f"(🚫 исключены: {', '.join(blocked_stations_found)})")
            
            return {'passed': True, 'reason': ' '.join(status_parts)}
        else:
            blocked_info = f" (исключены: {', '.join(blocked_stations_found)})" if blocked_stations_found else ""
            return {'passed': False, 'reason': f'Ближайшая валидная станция {closest_station.station_name} в {closest_minutes} мин (> {max_distance} мин){blocked_info}'}


class CharacteristicsFilter(BaseFilter):
    """Фильтр по характеристикам квартиры"""
    
    async def check(self, apartment: Apartment) -> Dict[str, Any]:
        # Проверяем площадь
        if apartment.area:
            if self.config.min_area and apartment.area < self.config.min_area:
                return {'passed': False, 'reason': f'Площадь слишком маленькая: {apartment.area} м²'}
            
            if self.config.max_area and apartment.area > self.config.max_area:
                return {'passed': False, 'reason': f'Площадь слишком большая: {apartment.area} м²'}
        
        # Проверяем количество комнат
        if apartment.rooms and self.config.allowed_rooms:
            if apartment.rooms not in self.config.allowed_rooms:
                return {'passed': False, 'reason': f'Неподходящее количество комнат: {apartment.rooms}'}
        
        # Проверяем этаж
        if apartment.floor:
            if self.config.min_floor and apartment.floor < self.config.min_floor:
                return {'passed': False, 'reason': f'Этаж слишком низкий: {apartment.floor}'}
            
            if self.config.max_floor and apartment.floor > self.config.max_floor:
                return {'passed': False, 'reason': f'Этаж слишком высокий: {apartment.floor}'}
        
        return {'passed': True, 'reason': 'Характеристики соответствуют критериям'}


class QualityFilter(BaseFilter):
    """Фильтр качества объявления"""
    
    async def check(self, apartment: Apartment) -> Dict[str, Any]:
        # Проверяем длину заголовка
        if len(apartment.title) < self.config.min_title_length:
            return {'passed': False, 'reason': 'Слишком короткий заголовок'}
        
        title_lower = apartment.title.lower()
        
        # Проверяем заблокированные слова
        if self.config.blocked_keywords:
            for keyword in self.config.blocked_keywords:
                if keyword.lower() in title_lower:
                    return {'passed': False, 'reason': f'Содержит заблокированное слово: {keyword}'}
        
        # Проверяем обязательные слова
        if self.config.required_keywords:
            has_required = any(keyword.lower() in title_lower for keyword in self.config.required_keywords)
            if not has_required:
                return {'passed': False, 'reason': 'Не содержит обязательных слов'}
        
        return {'passed': True, 'reason': 'Качество объявления соответствует критериям'}


class MarketPriceFilter(BaseFilter):
    """Фильтр по соответствию рыночным ценам - находит квартиры дешевле рынка"""
    
    async def check(self, apartment: Apartment) -> Dict[str, Any]:
        if not apartment.price:
            return {'passed': False, 'reason': 'Цена не указана'}
        
        # Получаем рыночный бенчмарк для квартиры
        market_data = await ApartmentService.get_market_benchmark(apartment)
        
        if not market_data['benchmark'] or not market_data['benchmark']['average_price']:
            return {'passed': True, 'reason': 'Недостаточно данных для сравнения с рынком'}
        
        price_deviation = market_data['price_deviation_percent']
        
        if price_deviation is None:
            return {'passed': True, 'reason': 'Не удалось рассчитать отклонение от рынка'}
        
        # Проверяем, что квартира дешевле рынка на 10% или больше
        discount_threshold = getattr(self.config, 'min_market_discount_percent', 10)
        
        if price_deviation <= -discount_threshold:
            benchmark_price = market_data['benchmark']['average_price']
            saving_amount = benchmark_price - apartment.price
            comparison_type = market_data['comparison_type']
            
            return {
                'passed': True,
                'reason': f'Дешевле рынка на {abs(price_deviation):.1f}% (экономия {saving_amount:,}₽, сравнение: {comparison_type})'
            }
        else:
            benchmark_price = market_data['benchmark']['average_price']
            if price_deviation >= 0:
                return {
                    'passed': False,
                    'reason': f'Дороже рынка на {price_deviation:.1f}% (рынок: {benchmark_price:,}₽)'
                }
            else:
                return {
                    'passed': False,
                    'reason': f'Скидка недостаточна: {abs(price_deviation):.1f}% < {discount_threshold}% (рынок: {benchmark_price:,}₽)'
                }


class DuplicateFilter(BaseFilter):
    """Фильтр дубликатов"""
    
    async def check(self, apartment: Apartment) -> Dict[str, Any]:
        if not self.config.check_duplicates:
            return {'passed': True, 'reason': 'Проверка дубликатов отключена'}
        
        # Проверяем, нет ли уже такой квартиры в production БД
        from .models import async_session
        from sqlalchemy import select, and_
        
        async with async_session() as session:
            existing_query = select(Apartment).where(
                and_(Apartment.cian_id == apartment.cian_id, Apartment.is_staging == False)
            )
            existing_result = await session.execute(existing_query)
            existing = existing_result.scalar_one_or_none()
            
            if existing:
                return {'passed': False, 'reason': 'Дубликат - уже есть в основной БД'}
        
        return {'passed': True, 'reason': 'Дубликат не обнаружен'}


class FilterService:
    """Основной сервис фильтрации"""
    
    def __init__(self, config: FilterConfig):
        self.config = config
        self.filters = [
            DuplicateFilter(config),
            PriceFilter(config),
        ]
        
        # Добавляем рыночный фильтр, если включен
        if config.enable_market_filter:
            self.filters.append(MarketPriceFilter(config))
            
        self.filters.extend([
            MetroFilter(config),
            CharacteristicsFilter(config),
            QualityFilter(config)
        ])
    
    async def process_apartments(self, limit: int = 50) -> Dict[str, int]:
        """
        Обрабатывает pending квартиры через фильтры
        
        Returns:
            Статистика: {'processed': int, 'approved': int, 'rejected': int}
        """
        stats = {'processed': 0, 'approved': 0, 'rejected': 0}
        
        # Получаем квартиры для обработки
        pending_apartments = await ApartmentService.get_pending_apartments(limit)
        
        for apartment in pending_apartments:
            try:
                # Проверяем через все фильтры
                all_passed = True
                rejection_reasons = []
                
                for filter_instance in self.filters:
                    result = await filter_instance.check(apartment)
                    
                    # Логируем результат фильтра
                    await ApartmentService.log_filter_result(
                        apartment.cian_id,
                        filter_instance.name,
                        'pass' if result['passed'] else 'fail',
                        result['reason']
                    )
                    
                    if not result['passed']:
                        all_passed = False
                        rejection_reasons.append(f"{filter_instance.name}: {result['reason']}")
                
                # Определяем финальный статус
                if all_passed:
                    # Квартира прошла все фильтры - одобряем
                    await ApartmentService.mark_apartment_processed(
                        apartment.cian_id, 
                        'approved',
                        'Прошла все фильтры'
                    )
                    
                    # Перемещаем в основную БД
                    await ApartmentService.move_to_production(apartment)
                    stats['approved'] += 1
                else:
                    # Отклоняем
                    reason = '; '.join(rejection_reasons[:3])  # Первые 3 причины
                    await ApartmentService.mark_apartment_processed(
                        apartment.cian_id,
                        'rejected',
                        reason
                    )
                    stats['rejected'] += 1
                
                stats['processed'] += 1
                
            except Exception as e:
                print(f"Ошибка при обработке квартиры {apartment.cian_id}: {e}")
                continue
        
        return stats
    



# Примеры конфигураций фильтров
DEFAULT_FILTER_CONFIG = FilterConfig(
    # Рыночные фильтры - основа системы
    enable_market_filter=True,
    min_market_discount_percent=10.0,  # минимум 10% скидка к рынку
    
    # Ценовые ограничения
    max_price=100_000_000,  # до 100 млн (широкие рамки)
    min_price=5_000_000,    # от 5 млн
    
    # Географические ограничения
    required_metro_distance=10,  # до 10 минут до метро (ближайшая валидная станция)
    # Станции загружаются из config/metro_config.py
    
    # Качество объявления
    min_title_length=20,
    blocked_keywords=['коммунальная', 'доля', 'хостел', 'общежитие'],
    check_duplicates=True
)

PREMIUM_FILTER_CONFIG = FilterConfig(
    # Рыночные фильтры - более строгие
    enable_market_filter=True,
    min_market_discount_percent=15.0,  # минимум 15% скидка к рынку
    
    # Ценовые ограничения
    max_price=80_000_000,   # до 80 млн
    min_price=20_000_000,   # от 20 млн
    max_price_per_sqm=400_000,  # до 400к за м²
    
    # Географические ограничения
    required_metro_distance=8,  # до 8 минут до метро (премиум требования)
    # Станции загружаются из config/metro_config.py
    # Только предпочитаемые станции для премиум конфигурации
    allowed_metro_stations=[
        'Красносельская', 'Комсомольская', 'Сокольники', 
        'Преображенская площадь', 'Сокол', 'Войковская'
    ],
    
    # Характеристики квартир
    min_area=50.0,  # от 50 м²
    allowed_rooms=[2, 3, 4],  # 2-4 комнаты
    min_floor=2,  # не первый этаж
    max_floor=20, # не выше 20 этажа
    
    # Качество объявления
    blocked_keywords=['студия', 'коммунальная', 'доля', 'комната', 'хрущевка', 'хостел'],
    check_duplicates=True
)

# Конфигурация только для поиска выгодных сделок
BARGAIN_HUNTER_CONFIG = FilterConfig(
    # Основной фокус - рыночные цены
    enable_market_filter=True,
    min_market_discount_percent=20.0,  # минимум 20% скидка к рынку!
    
    # Минимальные ограничения для поиска максимальных скидок
    max_price=150_000_000,  # широкие рамки
    min_price=3_000_000,
    required_metro_distance=30,  # можем пожертвовать удобством ради цены
    
    # Только базовые фильтры качества
    min_title_length=15,
    blocked_keywords=['доля', 'коммунальная'],
    check_duplicates=True
)

# Конфигурация для первоначального наполнения БД (без рыночного фильтра)
BOOTSTRAP_CONFIG = FilterConfig(
    # Отключаем рыночный фильтр для создания базы сравнения
    enable_market_filter=False,
    
    # Базовые ограничения - очень либеральные
    max_price=200_000_000,  # очень широкие рамки
    min_price=1_000_000,
    
    # НЕ требуем метро для первоначального наполнения
    required_metro_distance=None,  # отключаем проверку расстояния до метро
    # В bootstrap режиме бан-лист игнорируется (см. MetroFilter логику)
    
    # Минимальное качество
    min_title_length=5,  # очень либерально
    blocked_keywords=['доля', 'коммунальная'],  # минимум блокировок
    check_duplicates=True
)