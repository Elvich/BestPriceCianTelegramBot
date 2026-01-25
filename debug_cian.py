
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re

async def debug_parse():
    url = "https://www.cian.ru/cat.php?deal_type=sale&district[0]=1&engine_version=2&flat_share=2&floornl=1&foot_min=10&is_first_floor=0&minfloorn=6&object_type[0]=1&offer_type=flat&only_flat=1&only_foot=2&room2=1&sort=price_object_order"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate, br",
        "Cache-Control": "max-age=0",
        "Sec-Ch-Ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1"
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.get(url, ssl=False) as response:
            text = await response.text()
            print(f"Status: {response.status}")
            print(f"Length: {len(text)}")
            print("Snippet:")
            print(text[:1000])
            
            soup = BeautifulSoup(text, 'lxml')
            cards = soup.find_all('article', {'data-name': 'CardComponent'})
            print(f"Found CardComponent: {len(cards)}")
            
            cards2 = soup.find_all('div', class_=re.compile(r'--card--'))
            print(f"Found --card--: {len(cards2)}")
            
            if "captcha" in text.lower():
                print("CAPTCHA DETECTED!")

if __name__ == "__main__":
    asyncio.run(debug_parse())
