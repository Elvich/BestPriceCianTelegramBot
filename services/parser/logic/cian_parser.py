
import asyncio
import aiohttp
from aiohttp_socks import ProxyConnector
from bs4 import BeautifulSoup
import re
import random
import logging
from typing import List, Optional, Dict, Any
from core.config import config
from .proxy_manager import ProxyManager

logger = logging.getLogger(__name__)

class CianParser:
    """
    Асинхронный парсер для извлечения объявлений о недвижимости с сайта Циан.
    С поддержкой автоматической ротации прокси.
    """
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self.session = session
        self.proxy_manager = ProxyManager()
        self.current_proxy: Optional[str] = None
        
        # Имитируем реальный браузер на macOS для обхода блокировок (Chrome 131)
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Sec-Ch-Ua": '"Not A(Brand";v="99", "Google Chrome";v="131", "Chromium";v="131"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"macOS"',
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }

    async def initialize(self):
        """Initializes the proxy manager"""
        await self.proxy_manager.initialize()

    async def _get_current_session(self) -> aiohttp.ClientSession:
        """Возвращает текущую сессию, создавая новую с прокси при необходимости"""
        if self.session and not self.session.closed:
            return self.session
            
        # Get a new proxy
        self.current_proxy = await self.proxy_manager.get_proxy()
        logger.info(f"Using proxy: {self.current_proxy}")
        
        connector = None
        if self.current_proxy and self.current_proxy.startswith('socks'):
            connector = ProxyConnector.from_url(self.current_proxy)
            
        self.session = aiohttp.ClientSession(
            headers=self.headers, 
            connector=connector,
            timeout=aiohttp.ClientTimeout(total=config.REQUEST_TIMEOUT)
        )
        return self.session

    async def _reset_session(self):
        """Resets the current session (used on error)"""
        if self.session:
            await self.session.close()
        self.session = None

    async def close(self):
        """Zakryvaet sessiyu"""
        if self.session and not self.session.closed:
            await self.session.close()

    async def _fetch_page_content(self, url: str) -> Optional[str]:
        """Загружает контент страницы асинхронно с повторными попытками и ротацией прокси"""
        max_retries = config.MAX_RETRIES
        
        for attempt in range(max_retries):
            session = await self._get_current_session()
            
            try:
                # Настраиваем прокси для запроса (если HTTP)
                proxy_url = None
                if self.current_proxy and not self.current_proxy.startswith('socks'):
                    proxy_url = self.current_proxy
                
                async with session.get(url, proxy=proxy_url, ssl=config.VERIFY_SSL) as response:
                    # Проверяем на капчу или блокировку
                    if response.status == 403 or response.status == 429:
                        logger.warning(f"🚫 Blocked/Captcha ({response.status}) on {url} with {self.current_proxy}")
                        if self.current_proxy:
                            await self.proxy_manager.report_bad_proxy(self.current_proxy)
                        await self._reset_session()
                        continue
                        
                    if response.status == 200:
                        content = await response.text()
                        
                        # Проверка на капчу в контенте
                        if any(kw in content.lower() for kw in ['captcha', 'security check', 'мы хотим убедиться']):
                             logger.warning(f"🚫 Captcha detected in content on {url} with {self.current_proxy}")
                             if self.current_proxy:
                                 await self.proxy_manager.report_bad_proxy(self.current_proxy)
                             await self._reset_session()
                             continue
                             
                        return content
                    else:
                        logger.warning(f"⚠️ Status {response.status} loading {url}")
                        return None
                        
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                logger.error(f"❌ Network error on {url} (Attempt {attempt+1}/{max_retries}): {e}")
                if self.current_proxy:
                    await self.proxy_manager.report_bad_proxy(self.current_proxy)
                await self._reset_session()
                # Пауза перед повтором (увеличенная для снижения нагрузки и шанса блокировки)
                await asyncio.sleep(random.uniform(2, 5))
                
            except Exception as e:
                logger.error(f"❌ Unexpected error on {url}: {e}")
                await self._reset_session()
                
        logger.error(f"❌ Failed to fetch {url} after {max_retries} attempts")
        return None

    def _extract_metro_info(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Извлекает информацию о метро (станции и время)"""
        metro_blocks = soup.find_all('li', {'data-name': 'UndergroundItem'})
        if not metro_blocks:
            metro_blocks = soup.find_all('div', class_=re.compile(r'--underground-name--'))
        
        station_info = []
        for block in metro_blocks:
            try:
                name_elem = block.find('a', class_=re.compile(r'--underground-link--'))
                if not name_elem:
                    name_elem = block
                
                name = name_elem.get_text(strip=True) if name_elem else "Unknown"
                
                time_elem = block.find('span', class_=re.compile(r'--underground-time--'))
                if not time_elem:
                    parent = block.find_parent('li')
                    if parent:
                        time_elem = parent.find('span', class_=re.compile(r'--underground-time--'))
                
                time_val = time_elem.get_text(strip=True) if time_elem else ""
                station_info.append({'station': name, 'time': time_val})
            except Exception as e:
                logger.debug(f"Ошибка при парсинге метро: {e}")
                continue
                
        return station_info

    def _extract_floor_info(self, soup: BeautifulSoup) -> tuple[Optional[int], Optional[int]]:
        """Извлекает информацию об этаже и этажности"""
        floor_text = soup.find('div', string=re.compile(r'Этаж'))
        if floor_text:
            value_elem = floor_text.find_next_sibling('div')
            if value_elem:
                val = value_elem.get_text(strip=True)
                match = re.search(r'(\d+)\s*из\s*(\d+)', val)
                if match:
                    return int(match.group(1)), int(match.group(2))
                    
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

    def _extract_views(self, soup: BeautifulSoup) -> Optional[int]:
        """Извлекает количество просмотров за сегодня"""
        views_regex = re.compile(r'(\d+)\s+просмотр')
        views_block = soup.find('div', string=views_regex)
        
        if not views_block:
            links = soup.find_all('a', string=views_regex)
            if links:
                views_block = links[0]
                
        if views_block:
            text = views_block.get_text(strip=True)
            today_match = re.search(r'(\d+)\s+за\s+сегодня', text)
            if today_match:
                return int(today_match.group(1))
            return 0
        return None

    def _extract_rooms(self, title: str, soup: BeautifulSoup) -> Optional[int]:
        """Извлекает количество комнат"""
        # Из заголовка
        match = re.search(r'(\d+)-комн', title)
        if match:
            return int(match.group(1))
        if 'студия' in title.lower():
            return 0
            
        # Из характеристик на странице
        fact_items = soup.find_all('div', {'data-name': 'OfferFactItem'})
        for item in fact_items:
            label = item.find('div', class_=re.compile(r'--title--'))
            if label and 'количество комнат' in label.get_text(strip=True).lower():
                value = item.find('div', class_=re.compile(r'--value--'))
                if value:
                    v_text = value.get_text(strip=True)
                    if 'студия' in v_text.lower():
                        return 0
                    m = re.search(r'(\d+)', v_text)
                    if m:
                        return int(m.group(1))
        return None

    def _extract_area(self, title: str, soup: BeautifulSoup) -> Optional[float]:
        """Извлекает общую площадь"""
        # Из заголовка
        match = re.search(r'(\d+[\.,]?\d*)\s*м²', title)
        if match:
            return float(match.group(1).replace(',', '.'))
            
        # Из характеристик на странице
        fact_items = soup.find_all('div', {'data-name': 'OfferFactItem'})
        for item in fact_items:
            label = item.find('div', class_=re.compile(r'--title--'))
            if label and 'общая площадь' in label.get_text(strip=True).lower():
                value = item.find('div', class_=re.compile(r'--value--'))
                if value:
                    v_text = value.get_text(strip=True)
                    m = re.search(r'(\d+[\.,]?\d*)', v_text)
                    if m:
                        return float(m.group(1).replace(',', '.'))
        return None

    async def _deep_parse(self, url: str) -> Optional[Dict[str, Any]]:
        """Глубокий парсинг страницы с детальным извлечением данных"""
        html_content = await self._fetch_page_content(url)
        if not html_content:
            return None
            
        soup = BeautifulSoup(html_content, 'lxml')
        page_text = soup.get_text().lower()
        
        # Фильтрация по ключевым словам
        auction_keywords = ['аукцион', 'auction', 'торги', 'банкротство']
        deposit_keywords = ['залог', 'внесен залог', 'внесён залог', 'депозит', 'deposit', 'аванс']
        for kw in (auction_keywords + deposit_keywords):
            if kw in page_text:
                if len(kw) > 4:
                    logger.info(f"Skipping {url}: found keyword '{kw}'")
                    return None

        address_elem = soup.find('div', {'data-name': 'Geo'})
        address = address_elem.get_text(strip=True) if address_elem else "Unknown Address"
        
        # Получаем заголовок со страницы для более точного извлечения комнат/площади
        page_title_elem = soup.find('h1', {'data-name': 'OfferTitle'})
        page_title = page_title_elem.get_text(strip=True) if page_title_elem else ""
        
        floor, floors_total = self._extract_floor_info(soup)
        
        return {
            'address': address,
            'metro_stations': self._extract_metro_info(soup),
            'floor': floor,
            'floors_total': floors_total,
            'views_today': self._extract_views(soup),
            'rooms': self._extract_rooms(page_title, soup),
            'area': self._extract_area(page_title, soup)
        }

    async def parse_page(self, url: str) -> List[List[Any]]:
        """Парсит одну страницу списка объявлений асинхронно"""
        logger.info(f"Parsing page: {url}")
        html_content = await self._fetch_page_content(url)
        if not html_content:
            return []

        soup = BeautifulSoup(html_content, 'lxml')
        cards = soup.find_all('article', {'data-name': 'CardComponent'})
        if not cards:
             cards = soup.find_all('div', class_=re.compile(r'--card--'))

        if not cards:
             cards = soup.find_all('div', class_=re.compile(r'--card--'))
        
        if not cards:
            logger.warning(f"⚠️ 0 cards found! Page Title: {soup.title.string if soup.title else 'No Title'}")
            # Логируем начало контента для анализа проблемы (капча, изменение верстки)
            logger.info(f"Page content dump (first 500 chars): {soup.get_text()[:500]}")

        logger.info(f"Found {len(cards)} cards on page")
        
        apartments = []
        tasks = []
        # Ограничиваем количество одновременных запросов, чтобы не триггерить капчу
        semaphore = asyncio.Semaphore(2) 
        
        # Сначала собираем базовую информацию
        for card in cards:
            try:
                # Попытка 1: Поиск по частичному совпадению класса (более мягкий регекс)
                link_elem = card.find('a', class_=re.compile(r'--link'))
                
                # Попытка 2: Поиск по href (fallback), если класс не найден или изменился
                if not link_elem:
                    link_elem = card.find('a', href=re.compile(r'/flat/|/sale/flat/'))
                
                if not link_elem:
                    # Логируем начало HTML карточки для отладки, если ссылка не найдена
                    logger.warning(f"⚠️ Link not found for card. Content start: {str(card)[:100]}...")
                    continue

                href = link_elem.get('href')
                if not href: continue
                
                title_elem = card.find('span', {'data-mark': 'OfferTitle'}) or card.find('div', class_=re.compile(r'--title--'))
                title = title_elem.get_text(strip=True) if title_elem else "No Title"

                # Фильтрация по заголовку
                if any(kw in title.lower() for kw in ['аукцион', 'auction', 'торги', 'банкротство']):
                    continue

                price_elem = card.find('span', {'data-mark': 'MainPrice'}) or card.find('div', class_=re.compile(r'--price--'))
                price_str = price_elem.get_text(strip=True) if price_elem else "0"

                psqm_elem = card.find('p', {'data-mark': 'PriceInfo'})
                price_per_sqm = psqm_elem.get_text(strip=True) if psqm_elem else ""

                # Добавляем задачу на глубокий парсинг с ограничением конкурентности
                tasks.append(self._process_card(href, title, price_str, price_per_sqm, semaphore))
                
            except Exception as e:
                logger.error(f"Error parsing card basic info: {e}")

        # Выполняем глубокий парсинг параллельно
        results = await asyncio.gather(*tasks)
        for res in results:
            if res:
                apartments.append(res)

        return apartments

    async def _process_card(self, href, title, price_str, price_per_sqm, semaphore):
        """Вспомогательный метод для параллельной обработки карточки с семафором"""
        async with semaphore:
            try:
                # Более существенная задержка между запросами
                wait_time = random.uniform(config.MIN_PARSER_DELAY / 2, config.MAX_PARSER_DELAY / 2)
                logger.debug(f"Waiting {wait_time:.1f}s before deep parse of {href}")
                await asyncio.sleep(wait_time)
                
                details = await self._deep_parse(href)
                if details:
                    return [href, title, price_str, price_per_sqm, details]
            except Exception as e:
                logger.error(f"Deep parse error for {href}: {e}")
                return [href, title, price_str, price_per_sqm, {}]
        return None
