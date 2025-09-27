import requests
from bs4 import BeautifulSoup
import time
import os
from tqdm import tqdm
 
class Parser:
    """
    Парсер для извлечения объявлений о недвижимости с сайта Циан.
    
    Attributes:
        url (str): Базовый URL для парсинга
        write_to_file (bool): Флаг для сохранения результатов в файл
        start_page (int): Номер начальной страницы
        end_page (int): Номер конечной страницы
        headers (dict): HTTP заголовки для имитации браузера
        kvs (list): Список найденных объявлений
    """
    
    def __init__(self, url, write_to_file=False, start_page=1, end_page=17):
        self.url = url
        self.write_to_file = write_to_file
        self.start_page = start_page
        self.end_page = end_page

        # Имитируем браузер Chrome для обхода блокировок
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.133 Safari/537.36"
        }

    def _validate_params(self):
        """Валидация входных параметров"""
        if not self.url:
            raise ValueError('URL is empty')
        if self.start_page < 1 or self.end_page < self.start_page:
            raise ValueError('Invalid page range')

    def _build_page_url(self, page_number):
        """
        Формирует URL для конкретной страницы.
        
        Args:
            page_number (int): Номер страницы
            
        Returns:
            str: URL с параметром страницы или базовый URL для первой страницы
        """
        if page_number == 1:
            # Первая страница не требует параметра p
            return self.url
        else:
            # Определяем разделитель в зависимости от наличия параметров в URL
            separator = '&' if '?' in self.url else '?'
            return f"{self.url}{separator}p={page_number}"

    def _fetch_page_content(self, url):
        """Получает HTML содержимое страницы"""
        response = requests.get(url=url, headers=self.headers)
        return response.text

    def _parse_card(self, card):
        """
        Извлекает данные из одной карточки объявления.
        
        Args:
            card: BeautifulSoup элемент карточки объявления
            
        Returns:
            list: [ссылка, название, цена, цена_за_м2] или None при ошибке
        """
        try:
            # Извлекаем основные данные объявления
            link = card.find('a', class_='_93444fe79c--link--eoxce').get('href')
            name = card.find('span', {'data-mark': 'OfferTitle'}).get_text(strip=True)
            price_per_sqm = card.find('p', {'data-mark': 'PriceInfo'}).get_text(strip=True)
            price = card.find('span', {'data-mark': 'MainPrice'}).get_text(strip=True)
            
            return [link, name, price, price_per_sqm]
        except AttributeError as e:
            # Если структура страницы изменилась или элемент не найден
            print(f"Ошибка при парсинге карточки: {e}")
            return None

    def _parse_page(self, page_number):
        """Парсит одну страницу и возвращает список объявлений"""
        current_url = self._build_page_url(page_number)
        html_content = self._fetch_page_content(current_url)
        
        soup = BeautifulSoup(html_content, 'lxml')
        cards = soup.find_all('div', class_='_93444fe79c--card--ibP42')
        
        page_items = []
        for card in cards:
            parsed_card = self._parse_card(card)
            if parsed_card:  # Добавляем только успешно распарсенные карточки
                page_items.append(parsed_card)
        
        return page_items

    def _save_to_file(self):
        """Сохраняет результаты в файл"""
        filename = 'floats.txt'
        absolute_path = os.path.abspath(filename)
        print(f"\nСохраняем результаты ({len(self.kvs)} объявлений) в файл: {absolute_path}")
        
        with open(filename, 'a') as file:
            for kv in self.kvs:
                file.write(f'{kv[0]} - {kv[1]} - {kv[2]} - {kv[3]}\n')

    def parse(self):
        """Основной метод парсинга"""
        self.kvs = []
        self._validate_params()

        total_pages = self.end_page - self.start_page + 1
        total_items = 0
        
        # Создаем прогресс-бар для страниц
        with tqdm(total=total_pages, desc="Парсинг страниц", unit="стр") as pbar:
            for i in range(self.start_page, self.end_page + 1): 
                # Обновляем описание прогресс-бара
                pbar.set_description(f"Парсинг страницы {i}")
                
                # Парсим текущую страницу
                page_items = self._parse_page(i)
                self.kvs.extend(page_items)
                
                total_items += len(page_items)
                # Обновляем постфикс с общей статистикой
                pbar.set_postfix({
                    'найдено': len(page_items), 
                    'всего': total_items
                })
                
                # Обновляем прогресс-бар
                pbar.update(1)
                time.sleep(3)

        if self.write_to_file:
            self._save_to_file()

        return self.kvs
