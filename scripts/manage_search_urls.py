"""
Search URL Management Script

Helper utility to manage search URLs for the Cian parser.

Usage:
    python manage_search_urls.py list
    python manage_search_urls.py add --url URL --name NAME
    python manage_search_urls.py enable --id ID
    python manage_search_urls.py disable --id ID
    python manage_search_urls.py delete --id ID
"""

import argparse
import sys
import os
from datetime import datetime

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.database import SessionLocal, SearchUrl


def list_search_urls(active_only=False):
    """List all search URLs"""
    db = SessionLocal()
    try:
        query = db.query(SearchUrl)
        if active_only:
            query = query.filter(SearchUrl.is_active == True)
        
        search_urls = query.order_by(SearchUrl.id).all()
        
        if not search_urls:
            print("No search URLs found.")
            return
        
        print("=" * 80)
        print("SEARCH URLs")
        print("=" * 80)
        
        for su in search_urls:
            status = "✅ ACTIVE" if su.is_active else "❌ INACTIVE"
            last_parsed = su.last_parsed_at.strftime("%Y-%m-%d %H:%M") if su.last_parsed_at else "Never"
            
            print(f"\nID: {su.id}")
            print(f"Name: {su.name}")
            print(f"Status: {status}")
            print(f"Last parsed: {last_parsed}")
            print(f"URL: {su.url}")
            print("-" * 80)
        
        print(f"\nTotal: {len(search_urls)} search URL(s)")
        if not active_only:
            active_count = sum(1 for su in search_urls if su.is_active)
            print(f"Active: {active_count}")
    finally:
        db.close()


def add_search_url(url, name):
    """Add new search URL"""
    db = SessionLocal()
    try:
        # Check if URL already exists
        existing = db.query(SearchUrl).filter(SearchUrl.url == url).first()
        if existing:
            print(f"❌ Error: Search URL already exists with ID {existing.id}")
            print(f"   Name: {existing.name}")
            return False
        
        # Create new search URL
        search_url = SearchUrl(
            url=url,
            name=name,
            is_active=True
        )
        db.add(search_url)
        db.commit()
        db.refresh(search_url)
        
        print(f"✅ Successfully added search URL")
        print(f"   ID: {search_url.id}")
        print(f"   Name: {search_url.name}")
        print(f"   URL: {search_url.url}")
        return True
    except Exception as e:
        print(f"❌ Error adding search URL: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def enable_search_url(search_url_id):
    """Enable (activate) search URL"""
    db = SessionLocal()
    try:
        search_url = db.query(SearchUrl).filter(SearchUrl.id == search_url_id).first()
        if not search_url:
            print(f"❌ Error: Search URL with ID {search_url_id} not found")
            return False
        
        if search_url.is_active:
            print(f"ℹ️  Search URL '{search_url.name}' is already active")
            return True
        
        search_url.is_active = True
        db.commit()
        
        print(f"✅ Successfully enabled search URL")
        print(f"   ID: {search_url.id}")
        print(f"   Name: {search_url.name}")
        return True
    except Exception as e:
        print(f"❌ Error enabling search URL: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def disable_search_url(search_url_id):
    """Disable (deactivate) search URL"""
    db = SessionLocal()
    try:
        search_url = db.query(SearchUrl).filter(SearchUrl.id == search_url_id).first()
        if not search_url:
            print(f"❌ Error: Search URL with ID {search_url_id} not found")
            return False
        
        if not search_url.is_active:
            print(f"ℹ️  Search URL '{search_url.name}' is already inactive")
            return True
        
        search_url.is_active = False
        db.commit()
        
        print(f"✅ Successfully disabled search URL")
        print(f"   ID: {search_url.id}")
        print(f"   Name: {search_url.name}")
        return True
    except Exception as e:
        print(f"❌ Error disabling search URL: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def delete_search_url(search_url_id):
    """Delete search URL (with confirmation)"""
    db = SessionLocal()
    try:
        search_url = db.query(SearchUrl).filter(SearchUrl.id == search_url_id).first()
        if not search_url:
            print(f"❌ Error: Search URL with ID {search_url_id} not found")
            return False
        
        # Show info
        print(f"⚠️  About to delete search URL:")
        print(f"   ID: {search_url.id}")
        print(f"   Name: {search_url.name}")
        print(f"   URL: {search_url.url}")
        
        # Count linked offers
        offer_count = len(search_url.offers)
        if offer_count > 0:
            print(f"\n⚠️  WARNING: This search URL has {offer_count} linked offer(s)")
            print(f"   Deletion will remove the link, but offers will remain in database")
        
        # Confirm
        response = input("\nAre you sure? (yes/no): ")
        if response.lower() != 'yes':
            print("❌ Deletion cancelled")
            return False
        
        db.delete(search_url)
        db.commit()
        
        print(f"✅ Successfully deleted search URL ID {search_url_id}")
        return True
    except Exception as e:
        print(f"❌ Error deleting search URL: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(
        description='Manage search URLs for Cian parser',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # List all search URLs
  python manage_search_urls.py list
  
  # List only active search URLs
  python manage_search_urls.py list --active-only
  
  # Add new search URL
  python manage_search_urls.py add \\
    --url "https://www.cian.ru/cat.php?deal_type=sale&region=1&room1=1" \\
    --name "Москва, 1-комн, продажа"
  
  # Enable search URL
  python manage_search_urls.py enable --id 1
  
  # Disable search URL
  python manage_search_urls.py disable --id 1
  
  # Delete search URL (with confirmation)
  python manage_search_urls.py delete --id 1
        '''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List search URLs')
    list_parser.add_argument('--active-only', action='store_true', help='Show only active URLs')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add new search URL')
    add_parser.add_argument('--url', type=str, required=True, help='Search URL')
    add_parser.add_argument('--name', type=str, required=True, help='Human-readable name')
    
    # Enable command
    enable_parser = subparsers.add_parser('enable', help='Enable (activate) search URL')
    enable_parser.add_argument('--id', type=int, required=True, help='Search URL ID')
    
    # Disable command
    disable_parser = subparsers.add_parser('disable', help='Disable (deactivate) search URL')
    disable_parser.add_argument('--id', type=int, required=True, help='Search URL ID')
    
    # Delete command
    delete_parser = subparsers.add_parser('delete', help='Delete search URL')
    delete_parser.add_argument('--id', type=int, required=True, help='Search URL ID')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Execute command
    if args.command == 'list':
        list_search_urls(active_only=args.active_only)
    elif args.command == 'add':
        if not add_search_url(args.url, args.name):
            sys.exit(1)
    elif args.command == 'enable':
        if not enable_search_url(args.id):
            sys.exit(1)
    elif args.command == 'disable':
        if not disable_search_url(args.id):
            sys.exit(1)
    elif args.command == 'delete':
        if not delete_search_url(args.id):
            sys.exit(1)


if __name__ == "__main__":
    main()
