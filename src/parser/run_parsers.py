"""
Run Parsers - Orchestration script for Cian parsing workflow

This script runs both the listing parser and detail parser in sequence,
providing a convenient way to execute the full data collection workflow.

Usage:
    python run_parsers.py --url URL [options]

Examples:
    # Interactive mode (asks before updating details)
    python run_parsers.py --url "https://www.cian.ru/cat.php?..." --pages 5
    
    # Non-interactive mode (auto-proceeds)
    python run_parsers.py --url "https://..." --pages 5 --update-limit 20 --non-interactive
    
    # Listing only (no detail updates)
    python run_parsers.py --url "https://..." --pages 10 --listing-only
"""

import argparse
import sys
import time
import os
from datetime import datetime

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.parser.listing_parser import ListingParser
from src.parser.detail_parser import DetailParser
from src.scoring.calculate_scores import calculate_scores, show_statistics
from src.core.database import SessionLocal, Offer


def get_database_stats():
    """Get current database statistics"""
    db = SessionLocal()
    try:
        total_offers = db.query(Offer).count()
        active_offers = db.query(Offer).filter(Offer.is_active == True).count()
        updated_offers = db.query(Offer).filter(Offer.updated_at.isnot(None)).count()
        new_offers = db.query(Offer).filter(Offer.updated_at.is_(None)).count()
        
        return {
            'total': total_offers,
            'active': active_offers,
            'updated': updated_offers,
            'new': new_offers
        }
    finally:
        db.close()


def print_header(title):
    """Print formatted header"""
    print("\\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70 + "\\n")


def run_workflow(args):
    """Execute the full parsing workflow"""
    
    print_header("CIAN PARSER WORKFLOW")
    print(f"🕐 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if args.all_sources:
        print(f"🔗 Processing: ALL active sources from database")
    else:
        print(f"🔗 URL: {args.url}")
    print(f"📄 Pages per source: {args.pages}")
    print()
    
    # Phase 1: Listing Collection
    print_header("PHASE 1: LISTING COLLECTION")
    
    listing_parser = ListingParser()
    if args.all_sources:
        listing_parser.run_all_sources(
            max_pages=args.pages,
            max_offers=args.max_offers
        )
    else:
        listing_parser.run(
            start_url=args.url,
            max_pages=args.pages,
            max_offers=args.max_offers
        )
    
    # Show statistics after listing collection
    stats_after_listing = get_database_stats()
    
    print("\\n" + "─" * 70)
    print("DATABASE STATUS AFTER LISTING COLLECTION")
    print("─" * 70)
    print(f"📊 Total offers in DB: {stats_after_listing['total']}")
    print(f"✅ Active offers: {stats_after_listing['active']}")
    print(f"🆕 New offers (no details): {stats_after_listing['new']}")
    print(f"📝 Updated offers (with details): {stats_after_listing['updated']}")
    print("─" * 70)
    
    # Check if we should skip detail updates
    if args.listing_only:
        print("\\n✅ Listing collection complete. Skipping detail updates (--listing-only flag set).")
        return
    
    if stats_after_listing['new'] == 0 and not args.update_limit:
        print("\\n✅ All offers already have details. Use --update-limit to force updates.")
        return
    
    # Phase 2: Detail Updates
    print_header("PHASE 2: DETAIL UPDATES")
    
    # Determine update limit
    if args.update_limit:
        update_limit = args.update_limit
    elif args.non_interactive:
        # Auto-update new offers in non-interactive mode
        update_limit = min(stats_after_listing['new'], 50)  # Cap at 50 by default
    else:
        # Interactive mode: ask user
        suggested_limit = min(stats_after_listing['new'], 20)
        print(f"\\nℹ️  Found {stats_after_listing['new']} offers without details.")
        response = input(f"Update details for up to {suggested_limit} offers? (y/n): ")
        
        if response.lower() != 'y':
            print("\\n⏭️  Skipping detail updates.")
            return
        
        # Ask for custom limit
        custom_limit = input(f"Enter limit (press Enter for {suggested_limit}): ")
        if custom_limit.strip():
            try:
                update_limit = int(custom_limit)
            except ValueError:
                print(f"Invalid input, using default: {suggested_limit}")
                update_limit = suggested_limit
        else:
            update_limit = suggested_limit
    
    if update_limit == 0:
        print("\\n⏭️  Update limit is 0, skipping detail updates.")
        return
    
    print(f"\\n🔄 Updating details for up to {update_limit} offers...\\n")
    
    # Run detail parser
    detail_parser = DetailParser()
    detail_parser.run(
        limit=update_limit,
        max_age_hours=args.max_age_hours,
        prioritize_new=True  # Always prioritize new offers in workflow
    )
    
    # Phase 3: Scoring
    print_header("PHASE 3: SCORING CALCULATION")
    try:
        calculate_scores()
        show_statistics()
    except Exception as e:
        print(f"⚠️  Scoring calculation failed: {e}")
    
    # Final statistics
    stats_final = get_database_stats()
    
    print("\\n" + "─" * 70)
    print("FINAL DATABASE STATUS")
    print("─" * 70)
    print(f"📊 Total offers: {stats_final['total']}")
    print(f"✅ Active offers: {stats_final['active']}")
    print(f"🆕 New offers (no details): {stats_final['new']}")
    print(f"📝 Updated offers (with details): {stats_final['updated']}")
    print("─" * 70)
    
    print(f"\\n🕐 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\\n✅ Workflow complete!\\n")


def main():
    parser = argparse.ArgumentParser(
        description='Orchestrated workflow for Cian listing collection and detail updates',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Interactive mode (default) - asks before updating details
  python run_parsers.py --url "https://www.cian.ru/cat.php?deal_type=sale&engine_version=2&offer_type=flat&region=1&room1=1" --pages 5
  
  # Non-interactive mode - auto-updates with specified limit
  python run_parsers.py --url "https://..." --pages 5 --update-limit 20 --non-interactive
  
  # Listing only (skip detail updates)
  python run_parsers.py --url "https://..." --pages 10 --listing-only
  
  # Update stale offers (older than 48 hours)
  python run_parsers.py --url "https://..." --pages 3 --update-limit 30 --max-age-hours 48
        '''
    )
    
    # Required arguments
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        '--url',
        type=str,
        help='Starting URL for the listing search'
    )
    group.add_argument(
        '--all-sources',
        action='store_true',
        help='Parse all active search URLs from the database'
    )
    
    # Listing parser options
    parser.add_argument(
        '--pages',
        type=int,
        default=1,
        help='Number of listing pages to parse (default: 1)'
    )
    
    parser.add_argument(
        '--max-offers',
        type=int,
        default=None,
        help='Maximum offers to collect in listing phase (optional)'
    )
    
    # Detail parser options
    parser.add_argument(
        '--update-limit',
        type=int,
        default=None,
        help='Maximum offers to update with details (optional, will prompt if not set)'
    )
    
    parser.add_argument(
        '--max-age-hours',
        type=int,
        default=None,
        help='Only update offers older than N hours (optional)'
    )
    
    # Workflow options
    parser.add_argument(
        '--listing-only',
        action='store_true',
        help='Only collect listings, skip detail updates'
    )
    
    parser.add_argument(
        '--non-interactive',
        action='store_true',
        help='Run without prompts (requires --update-limit or uses defaults)'
    )
    
    parser.add_argument(
        '--loop',
        action='store_true',
        help='Run the workflow in a continuous loop'
    )
    
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Interval between loop cycles in minutes (default: 60)'
    )
    
    args = parser.parse_args()
    
    if args.loop:
        print_header("LOOP MODE ACTIVATED")
        print(f"🔄 Cycle interval: {args.interval} minutes")
        print(f"🚀 Initial run starting now...")
        
        while True:
            try:
                run_workflow(args)
                print(f"\\n😴 Sleeping for {args.interval} minutes... (Next run at: "
                      f"{(datetime.now().replace(second=0, microsecond=0) + __import__('datetime').timedelta(minutes=args.interval)).strftime('%H:%M')})")
                time.sleep(args.interval * 60)
            except KeyboardInterrupt:
                print("\\n\\n⚠️  Loop interrupted by user.")
                sys.exit(0)
            except Exception as e:
                print(f"\\n\\n❌ Cycle failed: {e}")
                print(f"⏳ Retrying in 5 minutes...")
                time.sleep(300)
    else:
        try:
            run_workflow(args)
        except KeyboardInterrupt:
            print("\\n\\n⚠️  Workflow interrupted by user.")
            sys.exit(1)
        except Exception as e:
            print(f"\\n\\n❌ Workflow failed with error: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
