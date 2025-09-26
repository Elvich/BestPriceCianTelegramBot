import requests
from bs4 import BeautifulSoup
import time
from tqdm import tqdm
 
class Parser:
    def __init__(self, url, write_to_file=False, start_page=1, end_page=17):
        self.url = url
        self.write_to_file = write_to_file
        self.start_page = start_page
        self.end_page = end_page

        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.133 Safari/537.36"
        }

    def parse(self):
        self.kvs = []
        if not self.url:
            raise ValueError('URL is empty')
        if self.start_page < 1 or self.end_page < self.start_page:
            raise ValueError('Invalid page range')

        total_pages = self.end_page - self.start_page + 1
        total_items = 0
        
        # Создаем прогресс-бар для страниц
        with tqdm(total=total_pages, desc="Парсинг страниц", unit="стр") as pbar:
            for i in range(self.start_page, self.end_page + 1): 
                # Обновляем описание прогресс-бара
                pbar.set_description(f"Парсинг страницы {i}")
                
                # Формируем URL для текущей страницы
                if i == 1:
                    # Первая страница без параметра p
                    current_url = self.url
                else:
                    # Добавляем параметр p для остальных страниц
                    separator = '&' if '?' in self.url else '?'
                    current_url = f"{self.url}{separator}p={i}"
                
                q = requests.get(url=current_url, headers=self.headers)
                result = q.text

                soup = BeautifulSoup(result, 'lxml')
                cards = soup.find_all('div', class_='_93444fe79c--card--ibP42')

                for card in cards:
                    link = card.find('a', class_='_93444fe79c--link--eoxce').get('href')
                    name = card.find('span', {'data-mark': 'OfferTitle'}).get_text(strip=True)
                    price_per_sqm = card.find('p', {'data-mark': 'PriceInfo'}).get_text(strip=True)
                    price = card.find('span', {'data-mark': 'MainPrice'}).get_text(strip=True)

                    self.kvs.append([link, name, price, price_per_sqm])

                total_items += len(cards)
                # Обновляем постфикс с общей статистикой
                pbar.set_postfix({
                    'найдено': len(cards), 
                    'всего': total_items
                })
                
                # Обновляем прогресс-бар
                pbar.update(1)
                time.sleep(3)

        if self.write_to_file:
            with open('floats.txt', 'a') as file:
                for kv in self.kvs:
                    file.write(f'{kv[0]} - {kv[1]} - {kv[2]} - {kv[3]}\n')

        return self.kvs
