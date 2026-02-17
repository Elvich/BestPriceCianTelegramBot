#!/usr/bin/env python3
"""
Apartment Scoring Calculator
Calculates and stores scoring for all apartments in the database.
Max score: 200 points (100 quality + 100 market interest)
"""

from sqlalchemy import text
from database import engine, SessionLocal
from datetime import datetime


def calculate_scores():
    """Calculate scores for all offers and populate offer_scores table."""
    
    session = SessionLocal()
    
    try:
        print("🔄 Calculating scores for all apartments...")
        
        # Execute the scoring calculation query
        query = text("""
        WITH market_stats AS (
            SELECT 
                metro_name,
                rooms_count,
                property_type,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY price_per_m2) as median_price_m2
            FROM offer_details od
            JOIN offer_prices op ON od.offer_id = op.offer_id
            WHERE rooms_count IS NOT NULL 
              AND property_type IS NOT NULL
              AND EXISTS (
                SELECT 1 FROM offers WHERE id = od.offer_id AND is_active = TRUE
              )
            GROUP BY metro_name, rooms_count, property_type
        ),
        latest_data AS (
            SELECT DISTINCT ON (o.id)
                o.id,
                od.total_area,
                od.floor,
                od.floors_count,
                od.metro_name,
                od.metro_time,
                od.metro_transport,
                od.rooms_count,
                od.property_type,
                op.price_per_m2,
                COALESCE(os.views_today, 0) as views_today
            FROM offers o
            JOIN offer_details od ON o.id = od.offer_id
            JOIN offer_prices op ON o.id = op.offer_id
            LEFT JOIN offer_stats os ON o.id = os.offer_id
            WHERE o.is_active = TRUE
            ORDER BY o.id, op.scraped_at DESC
        ),
        scored_offers AS (
            SELECT 
                ld.id as offer_id,
                
                -- Discount percentage
                ROUND(((ms.median_price_m2 - ld.price_per_m2) / ms.median_price_m2 * 100)::numeric, 1) as discount_pct,
                
                -- === QUALITY SCORES (100 points) ===
                
                -- 1. PRICE (45 points)
                CASE
                    WHEN ((ms.median_price_m2 - ld.price_per_m2) / ms.median_price_m2 * 100) >= 20 THEN 45
                    WHEN ((ms.median_price_m2 - ld.price_per_m2) / ms.median_price_m2 * 100) >= 15 THEN 38
                    WHEN ((ms.median_price_m2 - ld.price_per_m2) / ms.median_price_m2 * 100) >= 10 THEN 32
                    WHEN ((ms.median_price_m2 - ld.price_per_m2) / ms.median_price_m2 * 100) >= 5 THEN 22
                    WHEN ((ms.median_price_m2 - ld.price_per_m2) / ms.median_price_m2 * 100) >= 0 THEN 10
                    ELSE 0
                END as price_score,
                
                -- 2. METRO (30 points)
                CASE
                    WHEN ld.metro_transport = 'walk' AND ld.metro_time <= 5 THEN 30
                    WHEN ld.metro_transport = 'walk' AND ld.metro_time <= 10 THEN 24
                    WHEN ld.metro_transport = 'walk' AND ld.metro_time <= 15 THEN 18
                    WHEN ld.metro_transport = 'walk' AND ld.metro_time <= 20 THEN 12
                    WHEN ld.metro_transport = 'transport' AND ld.metro_time <= 10 THEN 10
                    WHEN ld.metro_transport = 'transport' AND ld.metro_time <= 15 THEN 6
                    ELSE 0
                END as metro_score,
                
                -- 3. FLOOR (15 points)
                CASE
                    WHEN ld.floor > 1 AND ld.floor < ld.floors_count 
                         AND ld.floor BETWEEN 3 AND (ld.floors_count - 2) THEN 15
                    WHEN ld.floor > 1 AND ld.floor < ld.floors_count THEN 12
                    WHEN ld.floor = 1 THEN 3
                    WHEN ld.floor = ld.floors_count THEN 5
                    ELSE 8
                END as floor_score,
                
                -- 4. AREA (10 points)
                CASE
                    WHEN ld.total_area BETWEEN 38 AND 50 THEN 10
                    WHEN ld.total_area BETWEEN 50 AND 65 THEN 9
                    WHEN ld.total_area BETWEEN 65 AND 75 THEN 8
                    WHEN ld.total_area BETWEEN 30 AND 38 THEN 6
                    WHEN ld.total_area BETWEEN 75 AND 90 THEN 7
                    WHEN ld.total_area < 30 THEN 3
                    WHEN ld.total_area > 90 THEN 4
                    ELSE 5
                END as area_score,
                
                -- === MARKET INTEREST (100 points) ===
                
                -- 5. VIEWS TODAY (100 points) - views_today / 2, max 100
                LEAST(100, ROUND(ld.views_today / 2.0)) as views_score
                
            FROM latest_data ld
            JOIN market_stats ms ON 
                ld.metro_name = ms.metro_name AND 
                ld.rooms_count = ms.rooms_count AND 
                ld.property_type = ms.property_type
        )
        INSERT INTO offer_scores (
            offer_id,
            price_score,
            metro_score,
            floor_score,
            area_score,
            views_score,
            quality_score,
            market_interest_score,
            total_score,
            discount_pct,
            calculated_at
        )
        SELECT 
            offer_id,
            price_score,
            metro_score,
            floor_score,
            area_score,
            views_score,
            (price_score + metro_score + floor_score + area_score) as quality_score,
            views_score as market_interest_score,
            (price_score + metro_score + floor_score + area_score + views_score) as total_score,
            discount_pct,
            NOW()
        FROM scored_offers
        ON CONFLICT (offer_id) 
        DO UPDATE SET
            price_score = EXCLUDED.price_score,
            metro_score = EXCLUDED.metro_score,
            floor_score = EXCLUDED.floor_score,
            area_score = EXCLUDED.area_score,
            views_score = EXCLUDED.views_score,
            quality_score = EXCLUDED.quality_score,
            market_interest_score = EXCLUDED.market_interest_score,
            total_score = EXCLUDED.total_score,
            discount_pct = EXCLUDED.discount_pct,
            calculated_at = NOW()
        """)
        
        result = session.execute(query)
        session.commit()
        
        # Get count of scored offers
        count_query = text("SELECT COUNT(*) FROM offer_scores")
        count = session.execute(count_query).scalar()
        
        print(f"✅ Successfully calculated scores for {count} apartments")
        print(f"⏰ Calculation completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Show top 10 offers
        print("\n🏆 TOP 10 OFFERS BY SCORE:")
        top_query = text("""
            SELECT 
                o.cian_id,
                os.total_score,
                os.quality_score,
                os.views_score,
                os.discount_pct,
                od.metro_name
            FROM offer_scores os
            JOIN offers o ON os.offer_id = o.id
            JOIN offer_details od ON o.id = od.offer_id
            ORDER BY os.total_score DESC
            LIMIT 10
        """)
        
        top_results = session.execute(top_query).fetchall()
        
        print(f"{'CIAN ID':<12} {'Total':<8} {'Quality':<9} {'Interest':<9} {'Discount%':<11} {'Metro'}")
        print("-" * 80)
        for row in top_results:
            cian_id, total, quality, interest, discount, metro = row
            discount_str = f"{discount:.1f}%" if discount else "N/A"
            print(f"{cian_id:<12} {total:<8} {quality:<9} {interest:<9} {discount_str:<11} {metro}")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error calculating scores: {e}")
        raise
    finally:
        session.close()


def show_statistics():
    """Show scoring statistics."""
    session = SessionLocal()
    
    try:
        stats_query = text("""
            SELECT 
                COUNT(*) as total_offers,
                ROUND(AVG(total_score)::numeric, 1) as avg_score,
                MAX(total_score) as max_score,
                MIN(total_score) as min_score,
                COUNT(CASE WHEN total_score >= 160 THEN 1 END) as top_tier,
                COUNT(CASE WHEN total_score >= 130 AND total_score < 160 THEN 1 END) as high_tier,
                COUNT(CASE WHEN total_score >= 100 AND total_score < 130 THEN 1 END) as mid_tier,
                COUNT(CASE WHEN total_score < 100 THEN 1 END) as low_tier
            FROM offer_scores
        """)
        
        result = session.execute(stats_query).fetchone()
        
        if result and result[0] > 0:
            print("\n📊 SCORING STATISTICS:")
            print(f"Total offers scored: {result[0]}")
            print(f"Average score: {result[1]}")
            print(f"Score range: {result[3]} - {result[2]}")
            print(f"\n📈 DISTRIBUTION:")
            print(f"  🔥🔥🔥 Top Tier (160-200):    {result[4]} offers")
            print(f"  🔥 High Tier (130-159):       {result[5]} offers")
            print(f"  ⭐ Mid Tier (100-129):        {result[6]} offers")
            print(f"  ✅ Low Tier (<100):           {result[7]} offers")
        
    finally:
        session.close()


if __name__ == "__main__":
    print("=" * 80)
    print("🎯 APARTMENT SCORING CALCULATOR")
    print("=" * 80)
    
    calculate_scores()
    show_statistics()
    
    print("\n" + "=" * 80)
    print("✨ Done! Use this query to view sorted results:")
    print("   SELECT * FROM offer_scores ORDER BY total_score DESC;")
    print("=" * 80)
