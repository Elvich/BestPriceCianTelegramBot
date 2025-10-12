import os
import csv
import asyncio
import sys

# Добавляем путь к родительской директории
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from DB.apartment_service import ApartmentService

class Saver:
    def __init__(self, filename='apartments.csv', save_to_db=True, save_to_csv=False, use_staging=True):
        self.filename = filename
        self.save_to_db = save_to_db
        self.save_to_csv = save_to_csv
        self.use_staging = use_staging

    def save(self, data):
        """Сохраняет данные в базу данных и/или CSV файл"""
        print(f"\nСохраняем результаты ({len(data)} объявлений)...")
        
        # Сохраняем в базу данных (по умолчанию)
        if self.save_to_db:
            try:
                # Выбираем метод для сохранения
                service_name = "staging БД" if self.use_staging else "основную БД"
                
                # Проверяем, работает ли уже event loop
                loop = None
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    pass
                
                if loop is not None:
                    # Если event loop уже запущен, создаем задачу
                    import concurrent.futures
                    import threading
                    
                    def run_in_thread():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            if self.use_staging:
                                return new_loop.run_until_complete(ApartmentService.save_to_staging(data))
                            else:
                                return new_loop.run_until_complete(ApartmentService.save_apartments(data))
                        finally:
                            new_loop.close()
                    
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_in_thread)
                        stats = future.result(timeout=60)  # 60 секунд таймаут
                else:
                    # Если event loop не запущен, используем обычный способ
                    if self.use_staging:
                        stats = asyncio.run(ApartmentService.save_to_staging(data))
                    else:
                        stats = asyncio.run(ApartmentService.save_apartments(data))
                
                print(f"📊 Статистика сохранения в {service_name}:")
                print(f"   ✅ Создано новых: {stats['created']}")
                print(f"   🔄 Обновлено: {stats['updated']}")
                if stats['errors'] > 0:
                    print(f"   ❌ Ошибок: {stats['errors']}")
                
                # Показываем статистику для выбранной БД
                def get_stats_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(ApartmentService.get_statistics(staging_only=self.use_staging))
                    finally:
                        new_loop.close()
                
                if loop is not None:
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(get_stats_in_thread)
                        db_stats = future.result(timeout=30)
                else:
                    db_stats = asyncio.run(ApartmentService.get_statistics(staging_only=self.use_staging))
                
                if self.use_staging:
                    print(f"📈 Общая статистика staging БД:")
                    print(f"   Всего объявлений: {db_stats['total_apartments']}")
                    print(f"   Ожидают обработки: {db_stats['pending_apartments']}")
                    print(f"   Одобрено: {db_stats['approved_apartments']}")
                    print(f"   Отклонено: {db_stats['rejected_apartments']}")
                else:
                    print(f"📈 Общая статистика основной БД:")
                    print(f"   Всего объявлений: {db_stats['total_apartments']}")
                    print(f"   Активных: {db_stats['active_apartments']}")
                    print(f"   Средняя цена: {db_stats['average_price']:,} ₽")
                
            except Exception as e:
                print(f"❌ Ошибка при сохранении в БД: {e}")
                print("Сохраняем в CSV как резервный вариант...")
                self.save_to_csv = True
        
        # Сохраняем в CSV (опционально или как резерв)
        if self.save_to_csv:
            self._save_to_csv(data)
    
    def _save_to_csv(self, data):
        """Сохраняет данные в CSV файл (старый метод)"""
        self.clear_file()

        absolute_path = os.path.abspath(self.filename)
        print(f"💾 Сохраняем в CSV файл: {absolute_path}")

        with open(self.filename, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            
            writer.writerow(['Ссылка', 'Название', 'Цена', 'Цена за м²', 'Детали'])
            
            # Записываем данные
            for kv in data:
                writer.writerow(kv)

    def clear_file(self):
        """Удаляет файл с результатами, если он существует"""
        if os.path.exists(self.filename):
            os.remove(self.filename)
            print(f"🗑️  Удален существующий файл: {self.filename}")

# Для обратной совместимости
class CSVSaver(Saver):
    """Класс для сохранения только в CSV (старое поведение)"""
    def __init__(self, filename='apartments.csv'):
        super().__init__(filename, save_to_db=False, save_to_csv=True, use_staging=False)

class ProductionSaver(Saver):
    """Класс для прямого сохранения в основную БД (без staging)"""
    def __init__(self, filename='apartments.csv'):
        super().__init__(filename, save_to_db=True, save_to_csv=False, use_staging=False)