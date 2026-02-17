"""
Listing Parser - Fast collection of Cian offers

This parser quickly collects offer IDs and URLs from listing pages without
fetching detailed information. It's designed for bulk collection with minimal
delays to efficiently build the offer database.

Usage:
    python listing_parser.py --url URL [--pages N] [--max-offers N]

Example:
    python listing_parser.py \\
        --url "https://www.cian.ru/cat.php?deal_type=sale&engine_version=2&offer_type=flat&region=1&room1=1" \\
        --pages 5 \\
        --max-offers 100
"""

import os
import sys

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.database import SessionLocal, Offer, SearchUrl


class ListingParser:
    def __init__(self):
        self.ua = UserAgent()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
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
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.db_session = SessionLocal()
        
        # Statistics
        self.stats = {
            'total_seen': 0,
            'new_offers': 0,
            'existing_offers': 0,
            'failed_parses': 0
        }
        
        # Current search URL being processed
        self.current_search_url_id = None

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
                
        except Exception as e:
            print(f"⚠️ Error saving cookies: {e}")

    def get_html(self, url, params=None):
        """Fetch HTML with minimal delay between requests"""
        try:
            # Faster delays for listing pages (1-3 seconds instead of 3-7)
            delay = random.uniform(1.0, 3.0)
            print(f"Waiting {delay:.2f} seconds...")
            time.sleep(delay)
            
            response = self.session.get(url, params=params)
            response.raise_for_status()
            
            # Save cookies on success
            self.save_cookies()
            
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def parse_card(self, card_soup):
        """Extract basic info from a listing card"""
        try:
            # Extract link & ID
            link_el = card_soup.select_one('a[href^="https://www.cian.ru/sale/flat/"]')
            if not link_el:
                link_el = card_soup.select_one('a[href^="/sale/flat/"]')
            
            if not link_el:
                return None
                
            link = link_el['href']
            if link.startswith('/'):
                link = f"https://www.cian.ru{link}"
            
            # Extract ID from link
            match = re.search(r'/flat/(\d+)', link)
            if not match:
                return None
                
            cian_id = int(match.group(1))
            
            return {
                'cian_id': cian_id,
                'url': link
            }
        except Exception as e:
            print(f"Error parsing card: {e}")
            return None

    def get_or_create_search_url(self, url, name=None):
        """Get existing SearchUrl or create new one"""
        db = self.db_session
        
        # Try to find existing
        search_url = db.query(SearchUrl).filter(SearchUrl.url == url).first()
        
        if not search_url:
            # Create new
            search_url = SearchUrl(
                url=url,
                name=name or url[:100]  # Use URL as name if not provided
            )
            db.add(search_url)
            db.commit()
            db.refresh(search_url)
            print(f"📌 Created new search URL: {search_url.name} (ID: {search_url.id})")
        else:
            print(f"📌 Using existing search URL: {search_url.name} (ID: {search_url.id})")
        
        return search_url
    
    def update_search_url_timestamp(self, search_url_id):
        """Update last_parsed_at timestamp for search URL"""
        try:
            db = self.db_session
            search_url = db.query(SearchUrl).filter(SearchUrl.id == search_url_id).first()
            if search_url:
                search_url.last_parsed_at = datetime.now()
                db.commit()
        except Exception as e:
            print(f"Warning: Could not update search URL timestamp: {e}")

    def save_offers_batch(self, offers_data):
        """Save offers in batch for better performance"""
        if not offers_data:
            return
            
        try:
            db = self.db_session
            now = datetime.now()
            
            for data in offers_data:
                cian_id = data['cian_id']
                url = data['url']
                
                # Check if offer exists
                offer = db.query(Offer).filter(Offer.cian_id == cian_id).first()
                
                if offer:
                    # Update existing offer
                    offer.last_seen_at = now
                    offer.is_active = True
                    offer.search_url_id = self.current_search_url_id  # Update source
                    self.stats['existing_offers'] += 1
                else:
                    # Create new offer
                    offer = Offer(
                        cian_id=cian_id,
                        url=url,
                        is_active=True,
                        last_seen_at=now,
                        search_url_id=self.current_search_url_id  # Link to source
                    )
                    db.add(offer)
                    self.stats['new_offers'] += 1
            
            # Commit batch
            db.commit()
            self.stats['total_seen'] += len(offers_data)
            
        except Exception as e:
            print(f"Database error: {e}")
            self.db_session.rollback()

    def parse_listing_page(self, url):
        """Parse a single listing page and extract all offer cards"""
        html = self.get_html(url)
        if not html:
            return []
        
        soup = BeautifulSoup(html, 'html.parser')
        cards = soup.select('[data-name="CardComponent"]')
        
        if not cards:
            if 'captcha' in soup.text.lower():
                print("⚠️  CAPTCHA DETECTED! Consider increasing delays.")
            else:
                print("No cards found on this page.")
            return []
        
        print(f"Found {len(cards)} cards on page")
        
        offers_data = []
        for card in cards:
            card_data = self.parse_card(card)
            if card_data:
                offers_data.append(card_data)
            else:
                self.stats['failed_parses'] += 1
        
        return offers_data

    def run(self, start_url, max_pages=1, max_offers=None, search_url_name=None):
        """Main parsing loop"""
        # Get or create search URL in database
        search_url_obj = self.get_or_create_search_url(start_url, search_url_name)
        self.current_search_url_id = search_url_obj.id
        
        print("=" * 60)
        print("LISTING PARSER - Fast Offer Collection")
        print("=" * 60)
        print(f"Source: {search_url_obj.name}")
        print(f"Start URL: {start_url}")
        print(f"Max pages: {max_pages}")
        if max_offers:
            print(f"Max offers: {max_offers}")
        print()
        
        all_offers = []
        
        for page in range(1, max_pages + 1):
            print(f"\\n📄 Processing page {page}/{max_pages}...")
            
            # Build page URL
            if page == 1:
                current_url = start_url
            else:
                if 'p=' in start_url:
                    current_url = re.sub(r'p=\d+', f'p={page}', start_url)
                else:
                    separator = '&' if '?' in start_url else '?'
                    current_url = f"{start_url}{separator}p={page}"
            
            # Parse page
            offers_data = self.parse_listing_page(current_url)
            
            if offers_data:
                all_offers.extend(offers_data)
                
                # Save in batches of 50 for better performance
                if len(all_offers) >= 50:
                    print(f"💾 Saving batch of {len(all_offers)} offers...")
                    self.save_offers_batch(all_offers)
                    all_offers = []
            
            # Check max_offers limit
            if max_offers and self.stats['total_seen'] >= max_offers:
                print(f"\\n✅ Reached max_offers limit ({max_offers})")
                break
        
        # Save remaining offers
        if all_offers:
            print(f"💾 Saving final batch of {len(all_offers)} offers...")
            self.save_offers_batch(all_offers)
        
        # Update search URL timestamp
        self.update_search_url_timestamp(self.current_search_url_id)
        
        # Print summary
        self.print_summary()

    def print_summary(self):
        """Print collection statistics"""
        print("\\n" + "=" * 60)
        print("COLLECTION SUMMARY")
        print("=" * 60)
        print(f"✅ Total offers processed: {self.stats['total_seen']}")
        print(f"🆕 New offers added: {self.stats['new_offers']}")
        print(f"🔄 Existing offers updated: {self.stats['existing_offers']}")
        print(f"❌ Failed parses: {self.stats['failed_parses']}")
        print("=" * 60)

    def run_all_sources(self, max_pages=1, max_offers=None):
        """Parse all active search URLs from database"""
        db = self.db_session
        
        # Get all active search URLs
        search_urls = db.query(SearchUrl).filter(SearchUrl.is_active == True).all()
        
        if not search_urls:
            print("ℹ️  No active search URLs found in database.")
            print("   Use manage_search_urls.py to add search URLs.")
            return
        
        print("=" * 60)
        print("LISTING PARSER - Multi-Source Collection")
        print("=" * 60)
        print(f"Active sources: {len(search_urls)}")
        print(f"Pages per source: {max_pages}")
        if max_offers:
            print(f"Max offers per source: {max_offers}")
        print()
        
        # Process each search URL
        for idx, search_url in enumerate(search_urls, 1):
            print(f"\n[{idx}/{len(search_urls)}] Processing: {search_url.name}")
            print(f"URL: {search_url.url}")
            print("-" * 60)
            
            # Reset stats for this source
            source_stats_before = {
                'total_seen': self.stats['total_seen'],
                'new_offers': self.stats['new_offers'],
                'existing_offers': self.stats['existing_offers']
            }
            
            # Run parser for this source
            self.run(search_url.url, max_pages, max_offers)
            
            # Calculate stats for this source
            source_new = self.stats['new_offers'] - source_stats_before['new_offers']
            source_existing = self.stats['existing_offers'] - source_stats_before['existing_offers']
            source_total = self.stats['total_seen'] - source_stats_before['total_seen']
            
            print(f"Source summary: {source_total} offers ({source_new} new, {source_existing} existing)")
        
        print("\n" + "=" * 60)
        print("MULTI-SOURCE COLLECTION SUMMARY")
        print("=" * 60)
        print(f"Sources processed: {len(search_urls)}")
        print(f"✅ Total offers: {self.stats['total_seen']}")
        print(f"🆕 New offers: {self.stats['new_offers']}")
        print(f"🔄 Existing offers: {self.stats['existing_offers']}")
        print(f"❌ Failed parses: {self.stats['failed_parses']}")
        print("=" * 60)

    def __del__(self):
        """Close database session"""
        if hasattr(self, 'db_session'):
            self.db_session.close()


def main():
    parser = argparse.ArgumentParser(
        description='Fast collection of Cian offer listings',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Collect 1 page (default)
  python listing_parser.py --url "https://www.cian.ru/cat.php?deal_type=sale&engine_version=2&offer_type=flat&region=1&room1=1"
  
  # Collect 10 pages
  python listing_parser.py --url "https://..." --pages 10
  
  # Collect up to 500 offers
  python listing_parser.py --url "https://..." --pages 20 --max-offers 500
        '''
    )
    
    parser.add_argument(
        '--url',
        type=str,
        required=False,  # Not required if --all-sources is used
        help='Starting URL for the listing search'
    )
    
    parser.add_argument(
        '--pages',
        type=int,
        default=1,
        help='Number of pages to parse (default: 1)'
    )
    
    parser.add_argument(
        '--max-offers',
        type=int,
        default=None,
        help='Maximum number of offers to collect (optional)'
    )
    
    parser.add_argument(
        '--all-sources',
        action='store_true',
        help='Parse all active search URLs from database (ignores --url)'
    )
    
    parser.add_argument(
        '--name',
        type=str,
        default=None,
        help='Human-readable name for this search URL (only used with --url)'
    )
    
    args = parser.parse_args()
    
    # Run parser
    listing_parser = ListingParser()
    
    if args.all_sources:
        # Multi-source mode
        listing_parser.run_all_sources(
            max_pages=args.pages,
            max_offers=args.max_offers
        )
    else:
        # Single source mode
        if not args.url:
            parser.error('--url is required when not using --all-sources')
        
        listing_parser.run(
            start_url=args.url,
            max_pages=args.pages,
            max_offers=args.max_offers,
            search_url_name=args.name
        )


if __name__ == "__main__":
    main()
