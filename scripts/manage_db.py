"""
CLI утилита для управления базой данных объявлений о квартирах.
Предоставляет команды для просмотра статистики, поиска и управления данными.
"""

import asyncio
import sys
import argparse
from typing import Optional, List
from datetime import datetime, timedelta

from DB.apartment_service import ApartmentService
from DB.Models import async_session, Apartment, MetroStation
from utils.excel_exporter import ExcelExporter

async def show_statistics():
    """Показывает общую статистику по базе данных"""
    stats = await ApartmentService.get_statistics()
    
    print("📊 Статистика базы данных:")
    print(f"   Всего объявлений: {stats['total_apartments']}")
    print(f"   Активных: {stats['active_apartments']}")
    print(f"   Неактивных: {stats['inactive_apartments']}")
    print(f"   Средняя цена: {stats['average_price']:,} ₽")

async def search_apartments(
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    metro: Optional[List[str]] = None,
    limit: int = 10
):
    """Поиск объявлений с фильтрами"""
    print(f"🔍 Поиск объявлений (лимит: {limit}):")
    
    if min_price:
        print(f"   Минимальная цена: {min_price:,} ₽")
    if max_price:
        print(f"   Максимальная цена: {max_price:,} ₽")
    if metro:
        print(f"   Рядом с метро: {', '.join(metro)}")
    
    apartments = await ApartmentService.get_apartments(
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        metro_stations=metro,
        only_active=True
    )
    
    if not apartments:
        print("❌ Объявления не найдены")
        return
    
    print(f"\n✅ Найдено {len(apartments)} объявлений:")
    
    for i, apt in enumerate(apartments, 1):
        price_str = f"{apt.price:,} ₽" if apt.price else "цена не указана"
        price_per_sqm_str = f"({apt.price_per_sqm:,} ₽/м²)" if apt.price_per_sqm else ""
        
        # Информация о метро
        metro_info = []
        for metro_station in apt.metro_stations[:2]:  # Показываем только первые 2
            metro_info.append(f"{metro_station.station_name} {metro_station.travel_time}")
        metro_str = f" | 🚇 {', '.join(metro_info)}" if metro_info else ""
        
        # Адрес
        address_str = f" | 📍 {apt.address}" if apt.address else ""
        
        print(f"\n{i:2d}. {price_str} {price_per_sqm_str}")
        print(f"    {apt.title}")
        print(f"    🔗 {apt.url}")
        if metro_str or address_str:
            print(f"    {metro_str}{address_str}")

async def list_metro_stations():
    """Показывает список всех станций метро в базе"""
    async with async_session() as session:
        from sqlalchemy import select
        
        query = select(MetroStation.station_name).distinct().order_by(MetroStation.station_name)
        result = await session.execute(query)
        stations = result.scalars().all()
        
        print(f"🚇 Станции метро в базе ({len(stations)}):")
        for station in stations:
            print(f"   • {station}")

async def recent_additions(days: int = 7):
    """Показывает недавно добавленные объявления"""
    async with async_session() as session:
        from sqlalchemy import select, and_
        
        since_date = datetime.utcnow() - timedelta(days=days)
        
        query = select(Apartment).where(
            and_(
                Apartment.first_seen >= since_date,
                Apartment.is_active == True
            )
        ).order_by(Apartment.first_seen.desc()).limit(20)
        
        result = await session.execute(query)
        apartments = result.scalars().all()
        
        print(f"🆕 Объявления за последние {days} дней ({len(apartments)}):")
        
        for apt in apartments:
            price_str = f"{apt.price:,} ₽" if apt.price else "цена не указана"
            date_str = apt.first_seen.strftime("%d.%m.%Y %H:%M")
            print(f"   • {date_str} - {price_str} - {apt.title[:50]}...")

async def export_data(filename=None, max_price=None, min_price=None, metro=None, limit=500, stats_only=False):
    """Экспорт данных в Excel"""
    try:
        service = ApartmentService()
        exporter = ExcelExporter()
        
        if stats_only:
            # Экспорт только статистики
            if not filename:
                filename = f"statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            result_filename = await exporter.export_statistics_to_excel(filename)
            
            if result_filename:
                print(f"✅ Статистика экспортирована в файл: {result_filename}")
            else:
                print("❌ Ошибка при экспорте статистики")
        else:
            # Экспорт объявлений с фильтрами
            if not filename:
                filename = f"apartments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            
            # Экспортируем данные с учетом фильтров
            result_filename = await exporter.export_apartments_to_excel(
                filename=filename,
                limit=limit,
                min_price=min_price,
                max_price=max_price,
                metro_stations=metro
            )
            
            if result_filename:
                print(f"✅ Объявления экспортированы в файл: {result_filename}")
            else:
                print("❌ Ошибка при экспорте объявлений")
            
    except Exception as e:
        print(f"❌ Ошибка при экспорте: {e}")

def main():
    """Главная функция CLI"""
    parser = argparse.ArgumentParser(description='Управление базой данных объявлений')
    
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # Команда статистики
    subparsers.add_parser('stats', help='Показать статистику')
    
    # Команда поиска
    search_parser = subparsers.add_parser('search', help='Поиск объявлений')
    search_parser.add_argument('--min-price', type=int, help='Минимальная цена')
    search_parser.add_argument('--max-price', type=int, help='Максимальная цена')
    search_parser.add_argument('--metro', nargs='+', help='Станции метро')
    search_parser.add_argument('--limit', type=int, default=10, help='Лимит результатов')
    
    # Команда списка станций метро
    subparsers.add_parser('metro', help='Показать все станции метро')
    
    # Команда недавних добавлений
    recent_parser = subparsers.add_parser('recent', help='Недавно добавленные объявления')
    recent_parser.add_argument('--days', type=int, default=7, help='За сколько дней показать')
    
    # Команда экспорта в Excel
    export_parser = subparsers.add_parser('export', help='Экспорт данных в Excel')
    export_parser.add_argument('--filename', type=str, help='Имя файла для экспорта')
    export_parser.add_argument('--max-price', type=int, help='Максимальная цена')
    export_parser.add_argument('--min-price', type=int, help='Минимальная цена')
    export_parser.add_argument('--metro', nargs='+', help='Станции метро')
    export_parser.add_argument('--limit', type=int, default=500, help='Лимит записей')
    export_parser.add_argument('--stats', action='store_true', help='Экспорт статистики')
    
    args = parser.parse_args()
    
    if args.command == 'stats':
        asyncio.run(show_statistics())
    elif args.command == 'search':
        asyncio.run(search_apartments(
            min_price=args.min_price,
            max_price=args.max_price,
            metro=args.metro,
            limit=args.limit
        ))
    elif args.command == 'metro':
        asyncio.run(list_metro_stations())
    elif args.command == 'recent':
        asyncio.run(recent_additions(days=args.days))
    elif args.command == 'export':
        asyncio.run(export_data(
            filename=args.filename,
            max_price=args.max_price,
            min_price=args.min_price,
            metro=args.metro,
            limit=args.limit,
            stats_only=args.stats
        ))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()