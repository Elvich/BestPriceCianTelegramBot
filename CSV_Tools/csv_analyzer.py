import csv
import re

def read_apartments_csv(filename='apartments.csv'):
    """
    Читает CSV файл с объявлениями и выводит статистику.
    
    Args:
        filename (str): Имя CSV файла
    """
    try:
        # Читаем CSV файл
        with open(filename, 'r', encoding='utf-8') as file:
            reader = csv.reader(file)
            headers = next(reader)  # Читаем заголовки
            rows = list(reader)     # Читаем все данные
        
        print(f"📊 Статистика по файлу {filename}:")
        print(f"   Всего объявлений: {len(rows)}")
        print(f"   Столбцы: {headers}")
        
        print("\n🔝 Первые 5 записей:")
        for i, row in enumerate(rows[:5]):
            print(f"   {i+1}. {dict(zip(headers, row))}")
        
        # Ищем колонку с ценой (не за м²)
        price_column_idx = None
        for i, header in enumerate(headers):
            if 'цена' in header.lower() and 'м²' not in header.lower():
                price_column_idx = i
                break
        
        if price_column_idx is not None:
            print(f"\n💰 Статистика по ценам ({headers[price_column_idx]}):")
            # Извлекаем числовые значения из цен
            prices = []
            for row in rows:
                price_str = row[price_column_idx]
                # Убираем все символы кроме цифр
                price_digits = re.sub(r'[^\d]', '', price_str)
                if price_digits:
                    prices.append(int(price_digits))
            
            if prices:
                print(f"   Минимальная цена: {min(prices):,} ₽")
                print(f"   Максимальная цена: {max(prices):,} ₽")  
                print(f"   Средняя цена: {sum(prices) // len(prices):,} ₽")
                print(f"   Медианная цена: {sorted(prices)[len(prices)//2]:,} ₽")
        
    except FileNotFoundError:
        print(f"❌ Файл {filename} не найден.")
        print("   Сначала запустите парсер для создания CSV файла.")
    except Exception as e:
        print(f"❌ Ошибка при чтении файла: {e}")

if __name__ == "__main__":
    read_apartments_csv()