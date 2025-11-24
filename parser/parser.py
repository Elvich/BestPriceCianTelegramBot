import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from bs4 import BeautifulSoup
import time
from tqdm import tqdm
from config.config import config
 
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
    
    def __init__(self):
        # Имитируем браузер Chrome для обхода блокировок
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.133 Safari/537.36"
        }

    def _validate_params(self, url, start_page, end_page):
        """Валидация входных параметров"""
        if not url:
            raise ValueError('URL is empty')
        if start_page < 1 or end_page < start_page:
            raise ValueError('Invalid page range')

    def _build_page_url(self, url, page_number):
        """
        Формирует URL для конкретной страницы.
        
        Args:
            page_number (int): Номер страницы
            
        Returns:
            str: URL с параметром страницы или базовый URL для первой страницы
        """
        if page_number == 1:
            # Первая страница не требует параметра p
            return url
        else:
            # Определяем разделитель в зависимости от наличия параметров в URL
            separator = '&' if '?' in url else '?'
            return f"{url}{separator}p={page_number}"

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
            # Ищем ссылку с data-name="TitleComponent" или просто первую ссылку
            link_el = card.find('a', {'data-name': 'TitleComponent'})
            if not link_el:
                link_el = card.find('a') # Fallback
                
            link = link_el.get('href')
            
            name_el = card.find('span', {'data-mark': 'OfferTitle'})
            name = name_el.get_text(strip=True) if name_el else "Без названия"
            
            price_per_sqm_el = card.find('p', {'data-mark': 'PriceInfo'})
            price_per_sqm = price_per_sqm_el.get_text(strip=True) if price_per_sqm_el else ""
            
            price_el = card.find('span', {'data-mark': 'MainPrice'})
            price = price_el.get_text(strip=True) if price_el else ""
            
            return [link, name, price, price_per_sqm]
        except Exception as e:
            # Если структура страницы изменилась или элемент не найден
            print(f"Ошибка при парсинге карточки: {e}")
            return None

    def _parse_page(self, url, page_number):
        """Парсит одну страницу и возвращает список объявлений"""
        current_url = self._build_page_url(url, page_number)
        html_content = self._fetch_page_content(current_url)
        
        soup = BeautifulSoup(html_content, 'lxml')
        # Обновленный селектор для карточек
        cards = soup.find_all('article', {'data-name': 'CardComponent'})
        
        # Если не нашли по новому селектору, пробуем старый (на всякий случай)
        if not cards:
             cards = soup.find_all('div', class_='_93444fe79c--card--ibP42')
        
        page_items = []
        for card in cards:
            parsed_card = self._parse_card(card)
            if parsed_card:  # Добавляем только успешно распарсенные карточки
                page_items.append(parsed_card)
        
        return page_items

    def _deep_parse(self, url):
        """Глубокий парсинг страницы с детальным извлечением данных"""
        html_content = self._fetch_page_content(url)
        soup = BeautifulSoup(html_content, 'lxml')

        # Извлекаем дополнительные данные из карточки
        details = {}
        
        # Извлекаем адрес
        # Ищем контейнер Geo, так как на странице много элементов с itemprop="name" (например, в хлебных крошках)
        geo_div = soup.find('div', {'data-name': 'Geo'})
        if geo_div:
            address_span = geo_div.find('span', {'itemprop': 'name'})
            details['address'] = address_span.get('content') if address_span else None
        else:
            # Fallback: пробуем найти первый span с itemprop="name" и атрибутом content
            address_span = soup.find('span', {'itemprop': 'name', 'content': True})
            details['address'] = address_span.get('content') if address_span else None
        
        # Извлекаем информацию о станциях метро
        details['metro_stations'] = self._extract_metro_info(soup)
        
        # Извлекаем информацию об этажах
        floor_info = self._extract_floor_info(soup)
        if floor_info:
            details['floor'] = floor_info.get('floor')
            details['floors_total'] = floor_info.get('floors_total')
        
        # Извлекаем просмотры за сутки
        details['views_per_day'] = self._extract_views(soup)

        return details

    def _extract_metro_info(self, soup):
        """
        Извлекает информацию о станциях метро и времени до них ТОЛЬКО ПЕШКОМ.
        Исключает время на транспорте/машине.
        
        Args:
            soup: BeautifulSoup объект страницы
            
        Returns:
            list: Список словарей с информацией о станциях метро (только пешком)
                  [{'station': 'Полежаевская', 'time': '8 мин пешком'}, ...]
        """
        metro_info = []
        
        try:
            # Ищем контейнер со списком станций метро
            metro_list = soup.find('ul', class_='xa15a2ab7--_065fb--undergrounds')
            
            if metro_list:
                # Находим все элементы станций
                metro_items = metro_list.find_all('li', class_='xa15a2ab7--d9f62d--underground')
                
                for item in metro_items:
                    try:
                        # Извлекаем название станции
                        station_link = item.find('a', class_='xa15a2ab7--d9f62d--underground_link')
                        station_name = station_link.get_text(strip=True) if station_link else None
                        
                        # Извлекаем время до станции
                        time_span = item.find('span', class_='xa15a2ab7--d9f62d--underground_time')
                        travel_time = time_span.get_text(strip=True) if time_span else None
                        
                        # ФИЛЬТРУЕМ: учитываем только время пешком
                        if station_name and travel_time and self._is_walking_time(travel_time):
                            metro_info.append({
                                'station': station_name,
                                'time': travel_time
                            })
                            
                    except Exception as e:
                        print(f"Ошибка при извлечении данных станции метро: {e}")
                        continue
                        
        except Exception as e:
            print(f"Ошибка при поиске информации о метро: {e}")
            
        return metro_info
    
    def _is_walking_time(self, time_text):
        """
        Проверяет, является ли указанное время временем пешком.
        Возвращает True, если текст содержит слова "пешком", но не содержит "транспорт" или "машин".
        """
        if not time_text:
            return False
            
        time_lower = time_text.lower()
        
        # Исключаем явные указания на транспорт/машину
        transport_keywords = [
            'на транспорте', 'на машине', 'автобус', 'транспорт', 
            'на авто', 'автомобиль', 'маршрутка', 'трамвай', 'троллейбус'
        ]
        
        for keyword in transport_keywords:
            if keyword in time_lower:
                return False
        
        # Принимаем если явно указано "пешком" или нет уточнения способа передвижения
        walking_keywords = ['пешком', 'пешки', 'пеший']
        
        # Если есть явное указание на пешком - принимаем
        for keyword in walking_keywords:
            if keyword in time_lower:
                return True
        
        # Если нет уточнения способа передвижения, считаем что это пешком
        # (по умолчанию на Cian время без уточнения = пешком)
        if 'мин' in time_lower and not any(word in time_lower for word in transport_keywords):
            return True
            
        return False
    
    def _extract_floor_info(self, soup):
        """
        Извлекает информацию об этаже квартиры.
        
        Args:
            soup: BeautifulSoup объект страницы
            
        Returns:
            dict: {'floor': int, 'floors_total': int} или None
        """
        import re
        
        try:
            # Ищем текст вида "5/21 этаж" или "5 из 21"
            # Типичные селекторы для информации об этаже
            floor_patterns = [
                # Вариант 1: текст с "этаж"
                (soup.find_all(string=re.compile(r'\d+/\d+\s*этаж', re.I)), r'(\d+)/(\d+)'),
                # Вариант 2: текст "X из Y"
                (soup.find_all(string=re.compile(r'\d+\s*из\s*\d+', re.I)), r'(\d+)\s*из\s*(\d+)'),
            ]
            
            for elements, pattern in floor_patterns:
                for element in elements:
                    text = element.strip()
                    match = re.search(pattern, text)
                    if match:
                        floor = int(match.group(1))
                        floors_total = int(match.group(2))
                        return {'floor': floor, 'floors_total': floors_total}
            
            # Если не нашли в тексте, ищем в атрибутах и структурированных данных
            # Попытка найти через data-атрибуты или специальные классы
            floor_containers = soup.find_all(['div', 'span'], class_=re.compile(r'floor', re.I))
            for container in floor_containers:
                text = container.get_text(strip=True)
                match = re.search(r'(\d+)/(\d+)', text)
                if match:
                    floor = int(match.group(1))
                    floors_total = int(match.group(2))
                    return {'floor': floor, 'floors_total': floors_total}
                    
        except Exception as e:
            print(f"Ошибка при извлечении информации об этаже: {e}")
        
        return None
    
    def _extract_views(self, soup):
        """
        Извлекает количество просмотров за сутки.
        
        Args:
            soup: BeautifulSoup объект страницы
            
        Returns:
            int: количество просмотров или None
        """
        import re
        
        try:
            # 1. Приоритетный поиск: кнопка статистики
            # <button class="..." data-name="OfferStats">
            #   ...
            #   1796 просмотров, 17 за сегодня, 1213 уникальных
            # </button>
            stats_button = soup.find('button', {'data-name': 'OfferStats'})
            if stats_button:
                text = stats_button.get_text(strip=True)
                # Ищем "X за сегодня"
                # Поддерживает форматы: "17 за сегодня", "1796 просмотров, 17 за сегодня"
                match = re.search(r'(\d+)\s*за сегодня', text)
                if match:
                    return int(match.group(1))
            
            # 2. Fallback: поиск по всему тексту (старая логика)
            # Ищем текст вида "X просмотров за сутки" или "X просмотров сегодня"
            view_patterns = [
                r'(\d+)\s*за сегодня',
                r'(\d+)\s*view',
            ]
            
            # Ищем по всему тексту страницы
            page_text = soup.get_text()
            
            for pattern in view_patterns:
                matches = re.findall(pattern, page_text, re.I)
                if matches:
                    # Берем первое найденное число
                    return int(matches[0])
            
            # 3. Fallback: поиск через классы
            view_containers = soup.find_all(['div', 'span'], class_=re.compile(r'view|за сегодня', re.I))
            for container in view_containers:
                text = container.get_text(strip=True)
                match = re.search(r'(\d+)', text)
                if match:
                    return int(match.group(1))
                    
        except Exception as e:
            print(f"Ошибка при извлечении просмотров: {e}")
        
        return None

    def parse(self, url, start_page=None, end_page=None, write_to_file=False, deep_parse=False):
        """Основной метод парсинга"""
        # Используем значения по умолчанию из конфигурации если не указаны
        if start_page is None:
            start_page = config.PARSER_DEFAULT_START_PAGE
        if end_page is None:
            end_page = config.PARSER_DEFAULT_END_PAGE
            
        self.kvs = []
        self._validate_params(url, start_page, end_page)

        total_pages = end_page - start_page + 1
        total_items = 0
        
        # Создаем прогресс-бар для страниц
        with tqdm(total=total_pages, desc="Парсинг страниц", unit="стр") as pbar:
            for i in range(start_page, end_page + 1): 
                # Обновляем описание прогресс-бара
                pbar.set_description(f"Парсинг страницы {i}")
                
                # Парсим текущую страницу
                page_items = self._parse_page(url= url, page_number=i)
                self.kvs.extend(page_items)
                
                total_items += len(page_items)
                # Обновляем постфикс с общей статистикой
                pbar.set_postfix({
                    'найдено': len(page_items), 
                    'всего': total_items
                })
                
                # Обновляем прогресс-бар
                pbar.update(1)
                time.sleep(config.PARSER_DELAY)

        if deep_parse:
            # Глубокий парсинг для каждого объявления
            detailed_kvs = []
            for item in tqdm(self.kvs, desc="Глубокий парсинг объявлений", unit="объявл"):
                try:
                    details = self._deep_parse(item[0])  # item[0] - ссылка на объявление
                except Exception as e:
                    print(f"Ошибка при глубоком парсинге {item[0]}: {e}")
                    details = None
                detailed_kvs.append(item + [details])  # Добавляем детали к основным данным
                time.sleep(config.PARSER_DEEP_DELAY)  # Пауза между запросами
            
            self.kvs = detailed_kvs  # Обновляем основной список на детализированный

        if write_to_file:
            self._save_to_file(source_url=url)

        return self.kvs
