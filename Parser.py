import requests
from bs4 import BeautifulSoup
import time
from tqdm import tqdm
from FileSaver import Saver
from config import config
 
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
            link = card.find('a', class_='_93444fe79c--link--eoxce').get('href')
            name = card.find('span', {'data-mark': 'OfferTitle'}).get_text(strip=True)
            price_per_sqm = card.find('p', {'data-mark': 'PriceInfo'}).get_text(strip=True)
            price = card.find('span', {'data-mark': 'MainPrice'}).get_text(strip=True)
            
            return [link, name, price, price_per_sqm]
        except AttributeError as e:
            # Если структура страницы изменилась или элемент не найден
            print(f"Ошибка при парсинге карточки: {e}")
            return None

    def _parse_page(self, url, page_number):
        """Парсит одну страницу и возвращает список объявлений"""
        current_url = self._build_page_url(url, page_number)
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
        """Сохраняет результаты в CSV файл"""
        Saver(filename='apartments.csv').save(data=self.kvs)

    def _deep_parse(self, url):
        """Глубокий парсинг страницы с детальным извлечением данных"""
        html_content = self._fetch_page_content(url)
        soup = BeautifulSoup(html_content, 'lxml')

        # Извлекаем дополнительные данные из карточки
        details = {}
        details['address'] = soup.find('span', {'itemprop': 'name'}).get('content')
        
        # Извлекаем информацию о станциях метро
        details['metro_stations'] = self._extract_metro_info(soup)

        return details

    def _extract_metro_info(self, soup):
        """
        Извлекает информацию о станциях метро и времени до них.
        
        Args:
            soup: BeautifulSoup объект страницы
            
        Returns:
            list: Список словарей с информацией о станциях метро
                  [{'station': 'Полежаевская', 'time': '8 мин.'}, ...]
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
                        
                        # Добавляем информацию если оба значения найдены
                        if station_name and travel_time:
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

    def parse(self, url, start_page=1, end_page=17, write_to_file=False, deep_parse=False):
        """Основной метод парсинга"""
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
                details = self._deep_parse(item[0])  # item[0] - ссылка на объявление
                detailed_kvs.append(item + [details])  # Добавляем детали к основным данным
                time.sleep(config.PARSER_DEEP_DELAY)  # Пауза между запросами
            
            self.kvs = detailed_kvs  # Обновляем основной список на детализированный

        if write_to_file:
            self._save_to_file()

        return self.kvs
