import os
import csv

class Saver:
    def __init__(self, filename = 'apartments.csv'):
        self.filename = filename

    def save(self, data):
        self.clear_file()

        absolute_path = os.path.abspath(self.filename)
        print(f"\nСохраняем результаты ({len(data)} объявлений) в файл: {absolute_path}")

        # Проверяем, существует ли файл для определения необходимости записи заголовков
        file_exists = os.path.exists(self.filename)

        with open(self.filename, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            
            # Записываем заголовки только если файл новый
            if not file_exists:
                writer.writerow(['Ссылка', 'Название', 'Цена', 'Цена за м²'])
            
            # Записываем данные
            for kv in data:
                writer.writerow(kv)

    def clear_file(self):
        """Удаляет файл с результатами, если он существует"""
        if os.path.exists(self.filename):
            os.remove(self.filename)
            print(f"\nУдален существующий файл: {self.filename}")