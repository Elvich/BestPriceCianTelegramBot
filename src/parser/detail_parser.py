"""
Detail Parser - Deep scraping and updating of Cian offer details

This parser selectively updates offer details for offers in the database.
It fetches detailed information, updates statistics, and maintains history.
Designed to run slower with longer delays to avoid detection.

Usage:
    python detail_parser.py [--limit N] [--max-age-hours N] [--prioritize-new]

Examples:
    # Update 10 oldest offers
    python detail_parser.py --limit 10
    
    # Update offers not updated in last 48 hours
    python detail_parser.py --limit 50 --max-age-hours 48
    
    # Prioritize new offers (never updated)
    python detail_parser.py --limit 20 --prioritize-new
"""

import os
import sys
import webbrowser
import requests
import re
import time
import random
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

try:
    from curl_cffi import requests as curl_requests
except ImportError:
    curl_requests = None

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.database import SessionLocal, Offer, OfferDetail, OfferPrice, OfferStat


class DetailParser:
    def __init__(self):
        self.ua = UserAgent()
        # Set a consistent User-Agent that matches the user's browser exactly
        self.current_ua = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36'
        self.headers = {
            'User-Agent': self.current_ua,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Referer': 'https://www.cian.ru/',
            'Cache-Control': 'max-age=0',
            'Sec-Ch-Ua': '"Not_A Brand";v="99", "Chromium";v="145", "Google Chrome";v="145"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"macOS"',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-User': '?1',
            'DNT': '1',
            'Connection': 'keep-alive'
        }
        
        # Use curl_cffi Session for better TLS fingerprinting
        if curl_requests:
            self.session = curl_requests.Session(impersonate="chrome120")
        else:
            self.session = requests.Session()
            
        self.session.headers.update(self.headers)
        self.db_session = SessionLocal()
        
        # Statistics
        self.stats = {
            'total_processed': 0,
            'successful_updates': 0,
            'failed_parses': 0,
            'inactive_offers': 0,
            'network_errors': 0
        }
        
        # Load cookies if exist
        self.load_cookies()

    def load_cookies(self):
        """Load cookies from data/cookies.txt if exists"""
        try:
            with open('data/cookies.txt', 'r', encoding='utf-8') as f:
                cookie_data = f.read().strip()
                
            if not cookie_data:
                return
                
            # Handle Netscape format or simple Header format
            if 'expiry' in cookie_data or '\t' in cookie_data:
                # Basic Netscape/curl format parser would go here, 
                # but for now let's assume simple header string "key=value; key2=value2"
                # or a simple dictionary-like structure if user pastes JSON
                pass
            
            # Simple "Cookie: " header string support
            if cookie_data.lower().startswith('cookie:'):
                cookie_data = cookie_data[7:].strip()
                
            # Parse "key=value; key2=value2" string
            cookie_dict = {}
            for item in cookie_data.split(';'):
                if '=' in item:
                    name, value = item.split('=', 1)
                    cookie_dict[name.strip()] = value.strip()
            
            self.session.cookies.update(cookie_dict)
            print(f"  🍪 Loaded {len(cookie_dict)} cookies from cookies.txt")
            
        except FileNotFoundError:
            pass
        except Exception as e:
            print(f"  ⚠️  Error loading cookies: {e}")

    def save_cookies(self):
        """Save current session cookies to cookies.txt"""
        try:
            cookies = self.session.cookies.get_dict()
            if not cookies:
                return
                
            # Format as "key=value; key2=value2"
            cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
            
            # Ensure data directory exists
            os.makedirs('data', exist_ok=True)
            
            with open('data/cookies.txt', 'w', encoding='utf-8') as f:
                f.write(cookie_str)
            print("  🍪 Cookies updated in data/cookies.txt")
                
        except Exception as e:
            print(f"  ⚠️  Error saving cookies: {e}")

    def get_html(self, url, params=None, max_retries=3):
        """Fetch HTML with retry logic and longer delays"""
        for attempt in range(max_retries):
            try:
                # Use slower delays for detail parser (7-15 seconds)
                wait_time = random.uniform(7.0, 15.0)
                print(f"  Waiting {wait_time:.2f} seconds...")
                time.sleep(wait_time)
                
                # Fetch page
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
                html = response.text
                
                # Improved block detection: 
                # If marker is present, it's a successful page even if it contains "captcha" keywords (false positives)
                marker = "window._cianConfig['frontend-offer-card']"
                if marker in html:
                    # Successful page, writing back cookies is done at the end of get_html
                    pass
                # Check for real captcha or bot detection markers
                elif 'checkbox-captcha-form' in html or 'captcha-container' in html or 'робот' in html.lower():
                    print(f"  ⚠️  REAL CAPTCHA DETECTED on attempt {attempt + 1}")
                    
                    # Manual intervention mechanism
                    print(f"  🛑 OPENING BROWSER for manual CAPTCHA solving...")
                    print(f"  👉 URL: {url}")
                    try:
                        webbrowser.open(url)
                    except Exception as e:
                        print(f"  ⚠️  Could not open browser: {e}")

                    print(f"  👉 Please solve the CAPTCHA in the opened browser window.")
                    print(f"  💡 If the page loads successfully in the browser, come back here.")
                    print(f"  💡 To use browser cookies: Save them to 'cookies.txt' and type 'reload'")
                    user_input = input(f"  ⌨️  Press ENTER to retry, 'reload' to load cookies, or 'skip': ")
                    
                    cmd = user_input.lower().strip()
                    if cmd == 'skip':
                        return None
                    elif cmd == 'reload':
                        self.load_cookies()
                        print(f"  🔄 Retrying with new cookies...")
                    else:
                        print(f"  🔄 Retrying...")
                    
                    time.sleep(3)
                    continue
                
                # If successful and not captcha, save cookies
                self.save_cookies()
                return html
            except requests.exceptions.RequestException as e:
                print(f"  ⚠️  Network error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(5)  # Wait before retry
                else:
                    self.stats['network_errors'] += 1
                    return None
        return None

    def parse_detail_page(self, url):
        """Parse detailed offer page and extract all information"""
        print(f"  📥 Fetching details from: {url}")
        html = self.get_html(url)
        
        if not html:
            return None
            
        if html == 'CAPTCHA':
            print(f"  ❌ Failed to fetch page: CAPTCHA block")
            return 'CAPTCHA'
        
        # Check if offer was removed (404 or not found indicators)
        indicators = [
            'объявление не найдено', 
            'страница не найдена', 
            'объявление снято с публикации',
            'квартира сдана',
            'квартира продана'
        ]
        
        lower_html = html.lower()
        if any(ind in lower_html for ind in indicators):
            print(f"  ❌ Offer not found or removed (Found indicator)")
            return 'REMOVED'
        
        try:
            # Extract JSON data from page
            start_marker = "window._cianConfig['frontend-offer-card']"
            concat_marker = ".concat("
            
            start_idx = html.find(start_marker)
            if start_idx == -1:
                print(f"  ⚠️  Config marker not found")
                return None
            
            concat_idx = html.find(concat_marker, start_idx)
            if concat_idx == -1:
                print(f"  ⚠️  Concat marker not found")
                return None
            
            array_start = html.find('[', concat_idx)
            if array_start == -1:
                print(f"  ⚠️  Array start not found")
                return None
            
            # Find matching closing bracket
            count = 0
            array_end = -1
            for i, char in enumerate(html[array_start:], start=array_start):
                if char == '[':
                    count += 1
                elif char == ']':
                    count -= 1
                    if count == 0:
                        array_end = i + 1
                        break
            
            if array_end == -1:
                print(f"  ⚠️  Array end not found")
                return None
            
            json_str = html[array_start:array_end]
            data_list = json.loads(json_str)
            
            default_state = next((item['value'] for item in data_list if item.get('key') == 'defaultState'), None)
            
            if not default_state or 'offerData' not in default_state:
                print(f"  ⚠️  Default state or offerData not found")
                return None
            
            offer = default_state['offerData'].get('offer')
            if not offer:
                print(f"  ⚠️  Offer object not found")
                return None
            
            building = offer.get('building', {})
            geo = offer.get('geo', {})
            bargain_terms = offer.get('bargainTerms', {})
            
            # Metro information
            undergrounds = geo.get('undergrounds', [])
            metro_name = None
            metro_time = None
            metro_transport = None
            if undergrounds:
                closest = undergrounds[0]
                metro_name = closest.get('name')
                metro_time = closest.get('travelTime')
                metro_transport = closest.get('travelType')
            
            # View statistics
            stats = default_state['offerData'].get('stats', {})
            views_str = stats.get('totalViewsFormattedString')
            views_total = None
            views_today = None
            
            if views_str:
                views_match = re.search(r'(\d+)\s+просмотров?,\s+(\d+)\s+за\s+сегодня', views_str)
                if views_match:
                    views_total = int(views_match.group(1))
                    views_today = int(views_match.group(2))
                else:
                    views_match_total = re.search(r'(\d+)\s+просмотров?', views_str)
                    if views_match_total:
                        views_total = int(views_match_total.group(1))
            
            # NEW: Extract additional fields
            rooms_count = offer.get('roomsCount')
            property_type = offer.get('offerType')
            balcony_count = offer.get('balconiesCount', 0)
            loggia_count = offer.get('loggiasCount', 0)
            
            # Auction and deposit information
            is_auction = False
            deposit_paid = None
            
            # Check auction flag in offer
            if offer.get('auction') is True:
                is_auction = True
            
            # Check in bargain terms for auction details
            if bargain_terms.get('auction'):
                is_auction = True
                if isinstance(bargain_terms.get('auction'), dict):
                    deposit_paid = bargain_terms.get('auction').get('depositPaid')

            # Build details dict
            details = {
                'description': offer.get('description'),
                'total_area': float(offer.get('totalArea')) if offer.get('totalArea') else None,
                'living_area': float(offer.get('livingArea')) if offer.get('livingArea') else None,
                'kitchen_area': float(offer.get('kitchenArea')) if offer.get('kitchenArea') else None,
                'floor': offer.get('floorNumber'),
                'floors_count': building.get('floorsCount'),
                'build_year': building.get('buildYear'),
                'material_type': building.get('materialType'),
                'metro_name': metro_name,
                'metro_time': metro_time,
                'metro_transport': metro_transport,
                'price': bargain_terms.get('price'),
                'price_per_m2': None,
                'views_total': views_total,
                'views_today': views_today,
                'rooms_count': rooms_count,
                'property_type': property_type,
                'balcony_count': balcony_count,
                'loggia_count': loggia_count,
                'is_auction': is_auction,
                'deposit_paid': deposit_paid,
                'extra_attributes': {
                    'address': geo.get('userInput')
                }
            }
            
            # Calculate price per m2
            if details['price'] and details['total_area']:
                try:
                    p = float(details['price'])
                    a = float(details['total_area'])
                    if a > 0:
                        details['price_per_m2'] = round(p / a, 2)
                except:
                    pass
            
            # Fallback for build_year
            if not details['build_year'] and 'deadline' in building:
                details['build_year'] = building['deadline'].get('year')
            
            print(f"  ✅ Successfully parsed details")
            return details
            
        except Exception as e:
            print(f"  ❌ Error parsing detail page: {e}")
            return None

    def save_offer_details(self, offer_id, detail_data):
        """Save or update offer details and history"""
        try:
            db = self.db_session
            now = datetime.now()
            
            # Update offer's updated_at timestamp
            offer = db.query(Offer).filter(Offer.id == offer_id).first()
            if offer:
                offer.updated_at = now
            
            # Upsert offer details
            offer_detail = db.query(OfferDetail).filter(OfferDetail.offer_id == offer_id).first()
            if not offer_detail:
                offer_detail = OfferDetail(offer_id=offer_id)
                db.add(offer_detail)
            
            offer_detail.description = detail_data['description']
            offer_detail.total_area = detail_data['total_area']
            offer_detail.living_area = detail_data['living_area']
            offer_detail.kitchen_area = detail_data['kitchen_area']
            offer_detail.floor = detail_data['floor']
            offer_detail.floors_count = detail_data['floors_count']
            offer_detail.build_year = detail_data['build_year']
            offer_detail.material_type = detail_data['material_type']
            offer_detail.metro_name = detail_data['metro_name']
            offer_detail.metro_time = detail_data['metro_time']
            offer_detail.metro_transport = detail_data['metro_transport']
            offer_detail.rooms_count = detail_data['rooms_count']
            offer_detail.property_type = detail_data['property_type']
            offer_detail.balcony_count = detail_data['balcony_count']
            offer_detail.loggia_count = detail_data['loggia_count']
            offer_detail.is_auction = detail_data['is_auction']
            offer_detail.deposit_paid = detail_data['deposit_paid']
            offer_detail.extra_attributes = detail_data['extra_attributes']
            
            # Insert price history
            if detail_data.get('price'):
                new_price = OfferPrice(
                    offer_id=offer_id,
                    price=detail_data['price'],
                    price_per_m2=detail_data['price_per_m2']
                )
                db.add(new_price)
            
            # Insert stats history
            if detail_data.get('views_total') is not None:
                new_stat = OfferStat(
                    offer_id=offer_id,
                    views_total=detail_data['views_total'],
                    views_today=detail_data['views_today']
                )
                db.add(new_stat)
            
            db.commit()
            self.stats['successful_updates'] += 1
            print(f"  💾 Saved to database")
            
        except Exception as e:
            print(f"  ❌ Database error: {e}")
            self.db_session.rollback()

    def mark_offer_inactive(self, offer_id):
        """Mark offer as inactive (removed from Cian)"""
        try:
            db = self.db_session
            offer = db.query(Offer).filter(Offer.id == offer_id).first()
            if offer:
                offer.is_active = False
                offer.updated_at = datetime.now()
                db.commit()
                self.stats['inactive_offers'] += 1
                print(f"  🔴 Marked as inactive")
        except Exception as e:
            print(f"  ⚠️  Error marking inactive: {e}")
            self.db_session.rollback()

    def get_offers_to_update(self, limit=10, max_age_hours=None, prioritize_new=False):
        """Query offers that need updating"""
        db = self.db_session
        
        query = db.query(Offer).filter(Offer.is_active == True)
        
        if prioritize_new:
            # Prioritize offers never updated
            query = query.order_by(
                Offer.updated_at.is_(None).desc(),  # NULL first
                Offer.updated_at.asc()  # Then oldest
            )
        elif max_age_hours:
            # Filter by age threshold
            threshold = datetime.now() - timedelta(hours=max_age_hours)
            query = query.filter(
                or_(
                    Offer.updated_at.is_(None),
                    Offer.updated_at < threshold
                )
            ).order_by(Offer.updated_at.asc().nullsfirst())
        else:
            # Default: oldest first
            query = query.order_by(Offer.updated_at.asc().nullsfirst())
        
        offers = query.limit(limit).all()
        return offers

    def run(self, limit=10, max_age_hours=None, prioritize_new=False):
        """Main update loop"""
        print("=" * 60)
        print("DETAIL PARSER - Deep Offer Updates")
        print("=" * 60)
        print(f"Update limit: {limit}")
        if max_age_hours:
            print(f"Max age: {max_age_hours} hours")
        if prioritize_new:
            print(f"Priority: New offers first")
        print()
        
        # Get offers to update
        offers = self.get_offers_to_update(limit, max_age_hours, prioritize_new)
        
        if not offers:
            print("ℹ️  No offers found matching criteria.")
            return
        
        print(f"Found {len(offers)} offers to update\\n")
        
        # Process each offer
        for idx, offer in enumerate(offers, 1):
            print(f"[{idx}/{len(offers)}] Processing cian_id={offer.cian_id}")
            self.stats['total_processed'] += 1
            
            # Parse details
            detail_data = self.parse_detail_page(offer.url)
            
            if detail_data == 'REMOVED':
                # Offer was removed
                self.mark_offer_inactive(offer.id)
            elif detail_data == 'CAPTCHA':
                print("\n🛑 CRITICAL: CAPTCHA detected. Stopping parser to avoid further blocking.")
                break
            elif detail_data:
                # Successfully parsed
                self.save_offer_details(offer.id, detail_data)
            else:
                # Parse failed
                self.stats['failed_parses'] += 1
                print(f"  ⚠️  Skipping due to parse failure")
            
            print()  # Blank line between offers
        
        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print update statistics"""
        print("=" * 60)
        print("UPDATE SUMMARY")
        print("=" * 60)
        print(f"📊 Total processed: {self.stats['total_processed']}")
        print(f"✅ Successful updates: {self.stats['successful_updates']}")
        print(f"🔴 Marked inactive: {self.stats['inactive_offers']}")
        print(f"❌ Failed parses: {self.stats['failed_parses']}")
        print(f"🌐 Network errors: {self.stats['network_errors']}")
        print("=" * 60)

    def __del__(self):
        """Close database session"""
        if hasattr(self, 'db_session'):
            self.db_session.close()


def main():
    parser = argparse.ArgumentParser(
        description='Deep scraping and updating of Cian offer details',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Update 10 oldest offers (default)
  python detail_parser.py --limit 10
  
  # Update offers not updated in last 48 hours
  python detail_parser.py --limit 50 --max-age-hours 48
  
  # Prioritize new offers first
  python detail_parser.py --limit 20 --prioritize-new
        '''
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Maximum number of offers to update (default: 10)'
    )
    
    parser.add_argument(
        '--max-age-hours',
        type=int,
        default=None,
        help='Only update offers older than N hours (optional)'
    )
    
    parser.add_argument(
        '--prioritize-new',
        action='store_true',
        help='Prioritize offers that have never been updated'
    )
    
    args = parser.parse_args()
    
    # Run parser
    detail_parser = DetailParser()
    detail_parser.run(
        limit=args.limit,
        max_age_hours=args.max_age_hours,
        prioritize_new=args.prioritize_new
    )


if __name__ == "__main__":
    main()
