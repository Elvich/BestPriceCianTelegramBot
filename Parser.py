import requests
from bs4 import BeautifulSoup
import time
from tqdm import tqdm
from FileSaver import Saver
 
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

    def parse(self, url, start_page=1, end_page=17, write_to_file=False):
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
                time.sleep(3)

        if write_to_file:
            self._save_to_file()

        return self.kvs
