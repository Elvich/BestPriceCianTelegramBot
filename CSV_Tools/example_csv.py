# Пример использования парсера с CSV выводом

from Parser import Parser

def main():
    """Демонстрация работы с CSV форматом"""
    
    print("🏠 Парсер объявлений Циан - CSV версия")
    print("=" * 50)
    
    # Создаем парсер
    parser = Parser(
        url='https://www.cian.ru/cat.php?deal_type=sale&engine_version=2&flat_share=2&floornl=1&foot_min=10&is_first_floor=0&minfloorn=6&object_type%5B0%5D=1&offer_type=flat&only_flat=1&only_foot=2&region=1&room2=1&sort=price_object_order',
        write_to_file=True, 
        start_page=1, 
        end_page=2  # Парсим 2 страницы для демонстрации
    )
    
    print("🔍 Начинаем парсинг...")
    results = parser.parse()
    
    print(f"\n✅ Парсинг завершен!")
    print(f"📋 Найдено объявлений: {len(results)}")
    print(f"💾 Результаты сохранены в файл: apartments.csv")
    
    # Показываем первые несколько результатов
    if results:
        print(f"\n🔝 Первые 3 объявления:")
        for i, apartment in enumerate(results[:3], 1):
            link, name, price, price_per_sqm = apartment
            print(f"   {i}. {name}")
            print(f"      💰 {price} ({price_per_sqm})")
            print(f"      🔗 {link}")
            print()
    
    print("💡 Подсказка: Используйте csv_analyzer.py для анализа результатов!")

if __name__ == "__main__":
    main()