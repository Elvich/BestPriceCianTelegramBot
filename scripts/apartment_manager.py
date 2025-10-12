"""
Обновленный скрипт фильтрации с объединенной архитектурой.
Использует одну БД и расширенный ApartmentService.
"""

import asyncio
import sys
import argparse
from datetime import datetime
import os

# Добавляем путь к родительской директории
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DB.filter_service import FilterService, FilterConfig, DEFAULT_FILTER_CONFIG, PREMIUM_FILTER_CONFIG, BARGAIN_HUNTER_CONFIG, BOOTSTRAP_CONFIG
from DB.apartment_service import ApartmentService

async def run_filter(config: FilterConfig, limit: int = 50, verbose: bool = False):
    """Запускает процесс фильтрации"""
    if verbose:
        print("🔍 Начинаем фильтрацию квартир...")
        print(f"   Лимит обработки: {limit}")
        
        # Показываем текущую статистику
        staging_stats = await ApartmentService.get_statistics(staging_only=True)
        production_stats = await ApartmentService.get_statistics(staging_only=False)
        print(f"\n📊 Статистика:")
        print(f"   Staging: {staging_stats['total_apartments']} (pending: {staging_stats['pending_apartments']})")
        print(f"   Production: {production_stats['total_apartments']} (active: {production_stats['active_apartments']})")
    
    # Создаем сервис фильтрации
    filter_service = FilterService(config)
    
    # Запускаем обработку
    start_time = datetime.now()
    results = await filter_service.process_apartments(limit)
    end_time = datetime.now()
    
    # Выводим результаты
    print(f"\n✅ Фильтрация завершена!")
    print(f"   Обработано: {results['processed']}")
    print(f"   Одобрено: {results['approved']}")
    print(f"   Отклонено: {results['rejected']}")
    print(f"   Время выполнения: {(end_time - start_time).total_seconds():.1f}с")
    
    if verbose and results['processed'] > 0:
        approval_rate = (results['approved'] / results['processed']) * 100
        print(f"   Процент одобрения: {approval_rate:.1f}%")

async def show_stats():
    """Показывает статистику по обеим частям БД"""
    staging_stats = await ApartmentService.get_statistics(staging_only=True)
    production_stats = await ApartmentService.get_statistics(staging_only=False)
    
    print("📊 Статистика единой базы данных:")
    print("\n🗄️ Staging данные (необработанные):")
    print(f"   Всего: {staging_stats['total_apartments']}")
    print(f"   Ожидают обработки: {staging_stats['pending_apartments']}")
    print(f"   Обработано: {staging_stats['processed_apartments']}")
    print(f"   ├── Одобрено: {staging_stats['approved_apartments']}")
    print(f"   └── Отклонено: {staging_stats['rejected_apartments']}")
    
    print("\n🏦 Production данные (готовые):")
    print(f"   Всего: {production_stats['total_apartments']}")
    print(f"   Активных: {production_stats['active_apartments']}")
    print(f"   Средняя цена: {production_stats['average_price']:,} ₽")

async def search_apartments(status: str = None, limit: int = 10, staging: bool = True):
    """Поиск объявлений"""
    from DB.models import async_session, Apartment
    from sqlalchemy import select, and_
    from sqlalchemy.orm import selectinload
    
    async with async_session() as session:
        query = select(Apartment).options(
            selectinload(Apartment.metro_stations)
        )
        
        conditions = [Apartment.is_staging == staging]
        
        if staging and status:
            conditions.append(Apartment.filter_status == status)
        elif not staging:
            conditions.append(Apartment.is_active == True)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        query = query.order_by(Apartment.first_seen.desc()).limit(limit)
        
        result = await session.execute(query)
        apartments = result.scalars().all()
    
    if not apartments:
        print("❌ Объявления не найдены")
        return
    
    status_emoji = {'pending': '⏳', 'approved': '✅', 'rejected': '❌'}
    db_name = "staging" if staging else "production"
    
    print(f"🔍 Найдено {len(apartments)} объявлений ({db_name}):\n")
    
    for i, apt in enumerate(apartments, 1):
        if staging:
            emoji = status_emoji.get(apt.filter_status, '❓')
        else:
            emoji = '✅' if apt.is_active else '❌'
        
        price_str = f"{apt.price:,} ₽" if apt.price else "цена не указана"
        
        metro_info = []
        for metro in apt.metro_stations[:2]:
            metro_info.append(f"{metro.station_name} ({metro.travel_time})")
        metro_str = f" | 🚇 {', '.join(metro_info)}" if metro_info else ""
        
        print(f"{i:2d}. {emoji} {price_str}")
        print(f"    {apt.title}")
        print(f"    📅 {apt.first_seen.strftime('%d.%m.%Y %H:%M')} | ID: {apt.cian_id}")
        
        if staging and apt.filter_reason:
            print(f"    💭 {apt.filter_reason}")
        
        print(f"    🔗 {apt.url}")
        if metro_str:
            print(f"    {metro_str}")
        print()

async def show_filter_logs(cian_id: str):
    """Показывает логи фильтрации"""
    from DB.models import async_session, FilterLog
    from sqlalchemy import select
    
    async with async_session() as session:
        query = select(FilterLog).where(
            FilterLog.apartment_cian_id == cian_id
        ).order_by(FilterLog.executed_at)
        
        result = await session.execute(query)
        logs = result.scalars().all()
    
    if not logs:
        print(f"❌ Логи для объявления {cian_id} не найдены")
        return
    
    print(f"📋 Логи фильтрации для объявления {cian_id}:\n")
    
    for log in logs:
        emoji = "✅" if log.result == "pass" else "❌"
        print(f"{emoji} {log.filter_name}")
        print(f"   {log.reason}")
        print(f"   {log.executed_at.strftime('%d.%m.%Y %H:%M:%S')}")
        print()

async def analyze_market_prices(rooms: int = None, metro: str = None):
    """Анализ рыночных цен"""
    
    print("📊 Анализ рыночных цен")
    print("=" * 40)
    
    # Общая статистика
    general_stats = await ApartmentService.calculate_weighted_average_price()
    
    print("🏠 Общая статистика рынка:")
    if general_stats['count'] > 0:
        print(f"   Средняя цена: {general_stats['average_price']:,} ₽")
        print(f"   Медианная цена: {general_stats['median_price']:,} ₽") 
        print(f"   Цена за м²: {general_stats['average_price_per_sqm']:,} ₽/м²")
        print(f"   Объявлений: {general_stats['count']}")
    else:
        print("   ❌ Недостаточно данных")
    
    # По количеству комнат
    if rooms:
        rooms_stats = await ApartmentService.calculate_weighted_average_price(rooms=rooms)
        
        print(f"\n🏠 Статистика для {rooms}-комнатных квартир:")
        if rooms_stats['count'] > 0:
            print(f"   Средняя цена: {rooms_stats['average_price']:,} ₽")
            print(f"   Медианная цена: {rooms_stats['median_price']:,} ₽")
            print(f"   Цена за м²: {rooms_stats['average_price_per_sqm']:,} ₽/м²")
            print(f"   Объявлений: {rooms_stats['count']}")
        else:
            print("   ❌ Недостаточно данных")
    
    # По станции метро
    if metro:
        metro_stats = await ApartmentService.calculate_weighted_average_price(
            rooms=rooms, metro_station=metro
        )
        
        metro_name = f" у метро {metro}" if metro else ""
        rooms_name = f"{rooms}-комнатных " if rooms else ""
        
        print(f"\n🚇 Статистика для {rooms_name}квартир{metro_name}:")
        if metro_stats['count'] > 0:
            print(f"   Средняя цена: {metro_stats['average_price']:,} ₽")
            print(f"   Медианная цена: {metro_stats['median_price']:,} ₽")
            print(f"   Цена за м²: {metro_stats['average_price_per_sqm']:,} ₽/м²")
            print(f"   Объявлений: {metro_stats['count']}")
        else:
            print("   ❌ Недостаточно данных")
    
    # Топ станций по количеству предложений
    print(f"\n📍 Анализ по станциям метро (топ-10):")
    from DB.models import async_session, Apartment, MetroStation
    from sqlalchemy import select, func, and_
    
    async with async_session() as session:
        # Запрос для получения топ станций
        query = select(
            MetroStation.station_name,
            func.count(MetroStation.apartment_id).label('count'),
            func.avg(Apartment.price).label('avg_price')
        ).join(Apartment).where(
            and_(Apartment.is_staging == False, Apartment.is_active == True)
        ).group_by(MetroStation.station_name).order_by(
            func.count(MetroStation.apartment_id).desc()
        ).limit(10)
        
        result = await session.execute(query)
        top_stations = result.all()
        
        for i, (station, count, avg_price) in enumerate(top_stations, 1):
            price_str = f"{avg_price:,.0f} ₽" if avg_price else "н/д"
            print(f"{i:2d}. {station}: {count} квартир, средняя цена {price_str}")

def create_custom_config() -> FilterConfig:
    """Интерактивное создание конфигурации фильтра"""
    print("🔧 Создание пользовательской конфигурации фильтра...")
    print("(Нажмите Enter для значений по умолчанию)")
    
    config = FilterConfig()
    
    # Цена
    max_price = input("Максимальная цена (руб): ").strip()
    if max_price:
        config.max_price = int(max_price)
    
    min_price = input("Минимальная цена (руб): ").strip()
    if min_price:
        config.min_price = int(min_price)
    
    # Метро
    metro_time = input("Максимальное время до метро (мин): ").strip()
    if metro_time:
        config.required_metro_distance = int(metro_time)
    
    # Станции метро
    metro_stations = input("Разрешенные станции метро (через запятую): ").strip()
    if metro_stations:
        config.allowed_metro_stations = [s.strip() for s in metro_stations.split(',')]
    
    # Площадь
    min_area = input("Минимальная площадь (м²): ").strip()
    if min_area:
        config.min_area = float(min_area)
    
    # Заблокированные слова
    blocked_words = input("Заблокированные слова в заголовке (через запятую): ").strip()
    if blocked_words:
        config.blocked_keywords = [w.strip() for w in blocked_words.split(',')]
    
    # Рыночный фильтр
    enable_market = input("Включить фильтр по рыночным ценам? (y/n, по умолчанию y): ").strip().lower()
    if enable_market != 'n':
        config.enable_market_filter = True
        
        market_discount = input("Минимальная скидка к рынку в % (по умолчанию 10): ").strip()
        if market_discount:
            config.min_market_discount_percent = float(market_discount)
        
        print(f"   🎯 Будут отбираться квартиры дешевле рынка на {config.min_market_discount_percent}%+")
    else:
        config.enable_market_filter = False
    
    print("✅ Конфигурация создана!")
    return config

def main():
    """Главная функция CLI"""
    parser = argparse.ArgumentParser(description='Фильтрация квартир в единой БД')
    
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # Команда запуска фильтра
    filter_parser = subparsers.add_parser('filter', help='Запустить фильтрацию')
    filter_parser.add_argument('--config', choices=['default', 'premium', 'bargain', 'bootstrap', 'custom'], 
                              default='default', help='Тип конфигурации')
    filter_parser.add_argument('--limit', type=int, default=50, 
                              help='Максимальное количество объявлений для обработки')
    filter_parser.add_argument('--verbose', '-v', action='store_true', 
                              help='Подробный вывод')
    
    # Команда статистики
    subparsers.add_parser('stats', help='Показать статистику единой БД')
    
    # Команда поиска
    search_parser = subparsers.add_parser('search', help='Поиск объявлений')
    search_parser.add_argument('--staging', action='store_true', help='Поиск в staging данных')
    search_parser.add_argument('--production', action='store_true', help='Поиск в production данных')
    search_parser.add_argument('--status', choices=['pending', 'approved', 'rejected'], 
                              help='Статус (только для staging)')
    search_parser.add_argument('--limit', type=int, default=10, help='Лимит результатов')
    
    # Команда просмотра логов
    logs_parser = subparsers.add_parser('logs', help='Показать логи фильтрации')
    logs_parser.add_argument('cian_id', help='ID объявления на Cian')
    
    # Команда анализа рынка
    market_parser = subparsers.add_parser('market', help='Анализ рыночных цен')
    market_parser.add_argument('--rooms', type=int, help='Количество комнат для анализа')
    market_parser.add_argument('--metro', help='Станция метро для анализа')
    
    args = parser.parse_args()
    
    if args.command == 'filter':
        # Выбираем конфигурацию
        if args.config == 'default':
            config = DEFAULT_FILTER_CONFIG
            print("📋 Используется конфигурация по умолчанию")
            print(f"   🎯 Минимальная скидка к рынку: {config.min_market_discount_percent}%")
        elif args.config == 'premium':
            config = PREMIUM_FILTER_CONFIG
            print("💎 Используется премиум конфигурация")
            print(f"   🎯 Минимальная скидка к рынку: {config.min_market_discount_percent}%")
        elif args.config == 'bargain':
            config = BARGAIN_HUNTER_CONFIG
            print("🎯 Используется конфигурация охотника за скидками")
            print(f"   💰 Минимальная скидка к рынку: {config.min_market_discount_percent}%")
        elif args.config == 'bootstrap':
            config = BOOTSTRAP_CONFIG
            print("🚀 Используется bootstrap конфигурация (для первоначального наполнения)")
            print("   📊 Рыночный фильтр отключен - создаем базу для сравнения")
        elif args.config == 'custom':
            config = create_custom_config()
        else:
            config = DEFAULT_FILTER_CONFIG
        
        asyncio.run(run_filter(config, args.limit, args.verbose))
        
    elif args.command == 'stats':
        asyncio.run(show_stats())
        
    elif args.command == 'search':
        staging = True
        if args.production:
            staging = False
        elif not args.staging:
            # По умолчанию ищем в staging если не указано
            staging = True
        
        asyncio.run(search_apartments(
            status=args.status,
            limit=args.limit,
            staging=staging
        ))
        
    elif args.command == 'logs':
        asyncio.run(show_filter_logs(args.cian_id))
    
    elif args.command == 'market':
        asyncio.run(analyze_market_prices(args.rooms, args.metro))
        
    else:
        parser.print_help()

if __name__ == "__main__":
    main()