
import requests
from bs4 import BeautifulSoup
import re
import time
import random

class CianParser:
    """
    Парсер для извлечения объявлений о недвижимости с сайта Циан.
    """
    
    def __init__(self):
        # Имитируем браузер Chrome для обхода блокировок
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.133 Safari/537.36"
        }
        
    def _fetch_page_content(self, url):
        """Загружает контент страницы"""
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при загрузке страницы {url}: {e}")
            return None

    def _extract_metro_info(self, soup):
        """Извлекает информацию о метро (станции и время)"""
        metro_blocks = soup.find_all('li', {'data-name': 'UndergroundItem'})
        if not metro_blocks:
            # Попробуем альтернативный селектор
            metro_blocks = soup.find_all('div', class_=re.compile(r'--underground-name--'))
        
        station_info = []
        for block in metro_blocks:
            try:
                # Извлекаем название станции
                name_elem = block.find('a', class_=re.compile(r'--underground-link--'))
                if not name_elem:
                    name_elem = block
                
                name = name_elem.get_text(strip=True) if name_elem else "Unknown"
                
                # Извлекаем время
                time_elem = block.find('span', class_=re.compile(r'--underground-time--'))
                if not time_elem:
                    # Ищем родительский контейнер, который может содержать время
                    parent = block.find_parent('li')
                    if parent:
                        time_elem = parent.find('span', class_=re.compile(r'--underground-time--'))
                
                time_val = time_elem.get_text(strip=True) if time_elem else ""
                
                station_info.append({'station': name, 'time': time_val})
            except Exception as e:
                print(f"Ошибка при парсинге метро: {e}")
                continue
                
        return station_info

    def _extract_floor_info(self, soup):
        """Извлекает информацию об этаже и этажности"""
        # Ищем блок с информацией об этаже
        # Обычно это выглядит как "5 из 12" или отдельные поля
        
        # Стратегия 1: Поиск по тексту "Этаж"
        floor_text = soup.find('div', string=re.compile(r'Этаж'))
        if floor_text:
            # Значение обычно в соседнем элементе или родительском блоке
            value_elem = floor_text.find_next_sibling('div')
            if value_elem:
                val = value_elem.get_text(strip=True)
                # Парсим строку вида "5 из 12"
                match = re.search(r'(\d+)\s*из\s*(\d+)', val)
                if match:
                    return int(match.group(1)), int(match.group(2))
                    
        # Стратегия 2: Поиск по data-name="OfferFactItem"
        fact_items = soup.find_all('div', {'data-name': 'OfferFactItem'})
        for item in fact_items:
            title = item.find('div', class_=re.compile(r'--title--'))
            if title and 'этаж' in title.get_text(strip=True).lower():
                value = item.find('div', class_=re.compile(r'--value--'))
                if value:
                    val = value.get_text(strip=True)
                    match = re.search(r'(\d+)\s*из\s*(\d+)', val)
                    if match:
                        return int(match.group(1)), int(match.group(2))

        return None, None

    def _extract_views(self, soup):
        """Извлекает количество просмотров"""
        # Ищем блок просмотров
        # Пример: "123 просмотра, 5 за сегодня"
        
        views_regex = re.compile(r'(\d+)\s+просмотр')
        views_block = soup.find('div', string=views_regex)
        
        if not views_block:
            # Попробуем найти по кнопке или ссылке с просмотрами
            links = soup.find_all('a', string=views_regex)
            if links:
                views_block = links[0]
                
        if views_block:
            text = views_block.get_text(strip=True)
            
            # Пытаемся извлечь просмотры за сегодня
            today_match = re.search(r'(\d+)\s+за\s+сегодня', text)
            if today_match:
                return int(today_match.group(1))
            
            # Если "за сегодня" нет, но есть общее число, возвращаем его (как approximation)
            # Но лучше вернуть None или 0, так как нам важна динамика
            return 0
            
        return None

    def _deep_parse(self, url):
        """Глубокий парсинг страницы с детальным извлечением данных"""
        html_content = self._fetch_page_content(url)
        if not html_content:
            return None
            
        soup = BeautifulSoup(html_content, 'lxml')

        # Дополнительная проверка на аукцион/залог на странице объявления
        page_text = soup.get_text().lower()
        auction_keywords = ['аукцион', 'auction']
        deposit_keywords = ['залог', 'внесен залог', 'внесён залог', 'депозит', 'deposit']
        all_keywords = auction_keywords + deposit_keywords
        
        for kw in all_keywords:
            if kw in page_text:
                # Проверяем контекст, чтобы не отсеять ложные срабатывания
                # Но для простоты пока считаем это маркером
                if len(kw) > 4: # Игнорируем короткие слова
                    print(f"Skipping {url}: found keyword '{kw}'")
                    return None

        # Извлекаем адрес
        address_elem = soup.find('div', {'data-name': 'Geo'})
        address = address_elem.get_text(strip=True) if address_elem else "Unknown Address"
        
        # Извлекаем метро
        metro_info = self._extract_metro_info(soup)
        
        # Извлекаем этаж
        floor, floors_total = self._extract_floor_info(soup)
        
        # Извлекаем просмотры
        views_today = self._extract_views(soup)

        return {
            'address': address,
            'metro_stations': metro_info,
            'floor': floor,
            'floors_total': floors_total,
            'views_today': views_today
        }

    def parse_page(self, url):
        """Парсит одну страницу списка объявлений"""
        print(f"Parsing page: {url}")
        html_content = self._fetch_page_content(url)
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, 'lxml')
        apartments = []
        
        # Находим карточки объявлений
        cards = soup.find_all('article', {'data-name': 'CardComponent'})
        
        if not cards:
             # Попробуем альтернативный, если верстка изменилась (Cian часто меняет классы)
             cards = soup.find_all('div', class_=re.compile(r'--card--'))

        print(f"Found {len(cards)} cards on page")

        for card in cards:
            try:
                # Ссылка
                link_elem = card.find('a', class_=re.compile(r'--link--'))
                if not link_elem:
                    continue
                href = link_elem.get('href')
                if not href:
                    continue
                
                # Заголовок
                title_elem = card.find('span', {'data-mark': 'OfferTitle'})
                if not title_elem:
                    # Fallback title extraction
                    title_elem = card.find('div', class_=re.compile(r'--title--'))
                title = title_elem.get_text(strip=True) if title_elem else "No Title"

                # Цена
                price_elem = card.find('span', {'data-mark': 'MainPrice'})
                if not price_elem:
                    price_elem = card.find('div', class_=re.compile(r'--price--'))
                price_str = price_elem.get_text(strip=True) if price_elem else "0"

                # Цена за м2
                price_per_sqm_elem = card.find('p', {'data-mark': 'PriceInfo'})
                price_per_sqm = price_per_sqm_elem.get_text(strip=True) if price_per_sqm_elem else ""

                # Фильтрация аукционов/залогов по заголовку
                lower_title = title.lower()
                auction_keywords = ['аукцион', 'auction', 'торги', 'банкротство']
                if any(kw in lower_title for kw in auction_keywords):
                    continue
                
                # Глубокий парсинг
                try:
                    # Добавляем случайную задержку перед глубоким парсингом, чтобы не банили
                    time.sleep(random.uniform(1.0, 3.0))
                    details = self._deep_parse(href)
                    
                    if details: # Если вернулся None, значит сработал фильтр deep_parse (например, аукцион)
                        apartments.append([href, title, price_str, price_per_sqm, details])
                    
                except Exception as e:
                    print(f"Deep parse error for {href}: {e}")
                    # В случае ошибки глубокого парсинга все равно добавляем базовую инфу
                    apartments.append([href, title, price_str, price_per_sqm, {}])

            except Exception as e:
                print(f"Error parsing card: {e}")
                continue

        return apartments
