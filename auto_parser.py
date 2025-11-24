import asyncio
import sys


from config.config import config
from parser.parser import Parser
from parser.url import CIAN_URLS
from DB.apartment_service import ApartmentService
from DB.filter_service import FilterService, DEFAULT_FILTER_CONFIG

async def parsing(url):
    """Прсинга данных с сайта"""
    
    print("Запуск парсинга квартир с Cian.ru")
    print("=" * 50)
    
    # Создаем парсер
    parser = Parser()
    
    try:
        # Парсим данные с реальной ссылки Cian
        print("🔍 Парсинг квартир с Cian.ru")
        url = url  # Используем переданный URL
        
        # Используем глубокий парсинг для получения полной информации
        apartments = parser.parse(url=url, start_page=config.PARSER_DEFAULT_START_PAGE, end_page=config.PARSER_DEFAULT_END_PAGE, write_to_file=False, deep_parse=True)

        if not apartments:
            print("❌ Квартиры не найдены")
            return
            
        print(f"✅ Найдено {len(apartments)} квартир")
        
        # Преобразуем данные парсера в объекты Apartment для БД
        print("🔄 Преобразование данных...")
        apartment_objects = []
        
        for item in apartments:
            try:
                # При глубоком парсинге: [link, name, price, price_per_sqm, details]
                link = item[0] if len(item) > 0 else ""
                name = item[1] if len(item) > 1 else ""
                price_str = item[2] if len(item) > 2 else ""
                price_per_sqm_str = item[3] if len(item) > 3 else ""
                details = item[4] if len(item) > 4 and item[4] else {}
                
                # Извлекаем cian_id из ссылки
                import re
                cian_id_match = re.search(r'/sale/flat/(\d+)/', link)
                cian_id = cian_id_match.group(1) if cian_id_match else f"demo_{hash(link) % 1000000}"
                
                # Парсим цену
                price = None
                if price_str:
                    price_numbers = re.findall(r'[\d\s]+', price_str.replace(' ', ''))
                    if price_numbers:
                        price = int(''.join(price_numbers[0].split()))
                
                # Парсим цену за м²
                price_per_sqm = None
                if price_per_sqm_str:
                    sqm_numbers = re.findall(r'(\d+)', price_per_sqm_str.replace(' ', ''))
                    if sqm_numbers:
                        price_per_sqm = int(sqm_numbers[0])
                
                # Создаем объект квартиры
                from DB.Models import Apartment
                apartment = Apartment(
                    cian_id=cian_id,
                    url=link,
                    title=name,
                    price=price,
                    price_per_sqm=price_per_sqm,
                    address=details.get('address', ''),
                    floor=details.get('floor'),
                    floors_total=details.get('floors_total'),
                    views_per_day=details.get('views_per_day'),
                    is_staging=True,
                    filter_status='pending'
                )
                
                # Устанавливаем price_segment сразу при создании
                if price:
                    if price < 15_000_000:
                        apartment.price_segment = 1
                    elif 15_000_000 <= price < 20_000_000:
                        apartment.price_segment = 2
                    elif 20_000_000 <= price <= 30_000_000:
                        apartment.price_segment = 3
                    # > 30M будет отклонено фильтром, но пока ставим None
                
                # Добавляем данные о метро из глубокого парсинга
                if 'metro_stations' in details and details['metro_stations']:
                    apartment.metro_data = details['metro_stations']
                
                apartment_objects.append(apartment)
                
            except Exception as e:
                print(f"⚠️ Ошибка обработки объявления: {e}")
                continue
        
        print(f"✅ Обработано {len(apartment_objects)} квартир")
        
        print("\n🔄 Пересмотр ранее отклоненных квартир из этого источника...")
        reprocess_stats = await ApartmentService.reprocess_rejected_apartments_for_source(url)
        if reprocess_stats['reprocessed'] > 0:
            print(f"✅ Переведено в pending для пересмотра: {reprocess_stats['reprocessed']} квартир")
        else:
            print("ℹ️ Нет отклоненных квартир для пересмотра")
        
        # Сохраняем в staging область базы данных
        print("\n📊 Сохранение в staging область...")
        saved_count = 0
        updated_count = 0
        
        from DB.Models import async_session
        from sqlalchemy import select, and_
        from datetime import datetime
        
        async with async_session() as session:
            for apartment in apartment_objects:
                try:
                    # Проверяем, существует ли уже такое объявление
                    existing = await session.scalar(
                        select(Apartment).where(
                            and_(
                                Apartment.cian_id == apartment.cian_id,
                                Apartment.is_staging == True
                            )
                        )
                    )
                    
                    if existing:
                        # Обновляем существующее
                        existing.price = apartment.price
                        existing.price_per_sqm = apartment.price_per_sqm
                        existing.title = apartment.title
                        existing.address = apartment.address
                        
                        # Сохраняем максимальное количество просмотров за все время
                        current_views = existing.views_per_day or 0
                        new_views = apartment.views_per_day or 0
                        existing.views_per_day = max(current_views, new_views)
                        
                        existing.last_updated = datetime.utcnow()
                        
                        # Важно: добавляем source_url
                        existing.source_url = url
                        
                        updated_count += 1
                        current_apartment = existing
                    else:
                        # Добавляем новое
                        apartment.first_seen = datetime.utcnow()
                        apartment.last_updated = datetime.utcnow()
                        
                        # Важно: добавляем source_url
                        apartment.source_url = url
                        
                        session.add(apartment)
                        saved_count += 1
                        current_apartment = apartment
                    
                    # Сохраняем данные о метро, если они есть
                    metro_data = getattr(apartment, 'metro_data', None)
                    if metro_data and isinstance(metro_data, list):
                        from DB.Models import MetroStation
                        from sqlalchemy import delete
                        
                        # Очищаем старые данные о метро для этой квартиры
                        if existing:
                            await session.execute(
                                delete(MetroStation).where(MetroStation.apartment_id == existing.id)
                            )
                        
                        # Добавляем новые данные о метро
                        for metro_info in metro_data:
                            metro_station = MetroStation(
                                apartment=current_apartment,
                                station_name=metro_info.get('station', ''),
                                travel_time=metro_info.get('time', '')
                            )
                            session.add(metro_station)
                    
                except Exception as e:
                    print(f"⚠️ Ошибка сохранения квартиры {apartment.cian_id}: {e}")
                    continue
            
            await session.commit()
        
        print(f"✅ Сохранено новых в staging: {saved_count}")
        print(f"🔄 Обновлено существующих: {updated_count}")
        
        # Показываем статистику обеих частей БД
        staging_stats = await ApartmentService.get_statistics(staging_only=True)
        production_stats = await ApartmentService.get_statistics(staging_only=False)
        
        print(f"\nСтатистика базы данных:")
        print(f"   Staging: {staging_stats['total_apartments']} (pending: {staging_stats['pending_apartments']})")
        print(f"   Production: {production_stats['total_apartments']} (средняя цена: {production_stats['average_price']:,.0f} ₽)")
        
        # Показываем несколько примеров из staging (получаем данные заново из БД)
        print(f"\n🏠 Примеры квартир в staging:")
        try:
            # Получаем staging данные напрямую
            async with async_session() as session:
                result = await session.execute(
                    select(Apartment).where(Apartment.is_staging == True).limit(3)
                )
                sample_apartments = result.scalars().all()
                
                for i, apartment in enumerate(sample_apartments, 1):
                    print(f"\n{i}. {apartment.title}")
                    if apartment.price:
                        print(f"   💰 {apartment.price:,} ₽")
                    if apartment.price_per_sqm:
                        print(f"   📊 {apartment.price_per_sqm:,} ₽/м²")
                    if apartment.address:
                        print(f"   📍 {apartment.address}")
                    # Получаем данные о метро для этой квартиры
                    metro_stations = await ApartmentService.get_metro_stations(apartment.id)
                    if metro_stations:
                        metro_info = []
                        for metro in metro_stations[:2]:
                            metro_info.append(f"{metro.station_name} ({metro.travel_time})")
                        print(f"   🚇 {', '.join(metro_info)}")
                    print(f"   🔗 {apartment.url}")
        except Exception as e:
            print(f" ⚠️ Не удалось загрузить примеры: {e}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        
    finally:
        print("\n✨ Демо парсинга завершено!")

async def filtering():
    print("\n" + "=" * 50)
    print("Фильтрация")
    print("=" * 50)
    
    try:
        # Проверяем, есть ли данные в staging
        staging_stats = await ApartmentService.get_statistics(staging_only=True)
        
        if staging_stats['pending_apartments'] == 0:
            print("⚠️  В staging нет неообработанных квартир")
            print("   Сначала запустите парсинг или добавьте данные")
            return
        
        print(f"📊 В staging области {staging_stats['pending_apartments']} квартир ожидают обработки")
        
        # Показываем анализ рынка перед фильтрацией
        print(f"\n📈 Быстрый анализ рыночных цен:")
        market_data = await ApartmentService.calculate_weighted_average_price()
        if market_data['count'] > 0:
            print(f"   Средняя цена: {market_data['average_price']:,} ₽")
            print(f"   Цена за м²: {market_data['average_price_per_sqm']:,} ₽/м²")
            print(f"   Данных: {market_data['count']} квартир за {market_data['days_analyzed']} дней")
        
        # Запускаем фильтрацию с рыночным фильтром
        print(f"\n🔍 Запуск фильтрации (минимальная скидка: {DEFAULT_FILTER_CONFIG.min_market_discount_percent}%)")
        filter_service = FilterService(DEFAULT_FILTER_CONFIG)
        results = await filter_service.process_apartments(limit=1000)
        
        print(f"\n✅ Результаты фильтрации:")
        print(f"   Обработано: {results['processed']}")
        print(f"   Одобрено: {results['approved']}")
        print(f"   Отклонено: {results['rejected']}")
        
        if results['processed'] > 0:
            approval_rate = (results['approved'] / results['processed']) * 100
            print(f"   Процент одобрения: {approval_rate:.1f}%")
        
        # Показываем обновленную статистику
        staging_stats_new = await ApartmentService.get_statistics(staging_only=True)
        production_stats_new = await ApartmentService.get_statistics(staging_only=False)
        
        print(f"\n📈 Обновленная статистика:")
        print(f"   Staging: {staging_stats_new['pending_apartments']} ожидают обработки")
        print(f"   Production: {production_stats_new['total_apartments']} готовых квартир")
        
    except Exception as e:
        print(f"❌ Ошибка фильтрации: {e}")



async def full_cycle(url):
    """Полный цикл: парсинг → staging → фильтрация → production"""
    
    print("=" * 50)
    
    # 1. Парсинг и сохранение в staging
    await parsing(url)
    
    # 2. Обычная фильтрация
    await filtering()


async def main():
    """Главная функция"""
    try:
        while True:
            for url in CIAN_URLS:
                await full_cycle(url)
                await asyncio.sleep(config.AUTO_PARSER_CYCLE_DELAY)  


    except ValueError as e:
        print(f"❌ Ошибка значения: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Неожиданная ошибка: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

