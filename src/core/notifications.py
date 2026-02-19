import os
import asyncio
import logging
import sys
from aiogram import Bot
from sqlalchemy import func
from dotenv import load_dotenv

# Add project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.database import SessionLocal, Offer, OfferDetail, OfferScore, OfferPrice, User

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(os.path.join(project_root, ".env"))

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def send_high_score_notifications():
    """Send notifications for new high-scored apartments to all active users."""
    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not found. Notifications skipped.")
        return

    bot = Bot(token=TOKEN)
    db = SessionLocal()
    
    try:
        # 1. Fetch active users to notify
        active_users = db.query(User).filter(User.is_active == True).all()
        if not active_users:
            logger.info("ℹ️ No active users found to notify.")
            return

        # 2. Fetch latest price subquery
        latest_price_sub = (
            db.query(
                OfferPrice.offer_id, 
                func.max(OfferPrice.scraped_at).label('max_scraped')
            )
            .group_by(OfferPrice.offer_id)
            .subquery()
        )

        # 3. Fetch high-scored offers that haven't been notified yet (Score >= 130)
        results = (
            db.query(Offer, OfferDetail, OfferScore, OfferPrice)
            .join(OfferDetail, Offer.id == OfferDetail.offer_id)
            .join(OfferScore, Offer.id == OfferScore.offer_id)
            .join(OfferPrice, Offer.id == OfferPrice.offer_id)
            .join(
                latest_price_sub,
                (OfferPrice.offer_id == latest_price_sub.c.offer_id) & 
                (OfferPrice.scraped_at == latest_price_sub.c.max_scraped)
            )
            .filter(OfferScore.total_score >= 130)
            .filter(OfferScore.is_notified == False)
            .filter(Offer.is_active == True)
            .all()
        )

        if not results:
            logger.info("ℹ️ No new high-scored apartments to notify.")
            return

        logger.info(f"🔔 Found {len(results)} new high-scored apartments. Sending notifications...")

        for offer, detail, score, price in results:
            # Determine Tier
            if score.total_score >= 160:
                tier_icon = "🔥🔥🔥"
                tier_name = "ТОП ВАРИАНТ"
            else:
                tier_icon = "🔥"
                tier_name = "ВЫСОКИЙ БАЛЛ"

            address = "Адрес не указан"
            if detail.extra_attributes and isinstance(detail.extra_attributes, dict):
                address = detail.extra_attributes.get('address', address)

            message_text = (
                f"{tier_icon} *{tier_name}!*\n"
                f"🎯 *Общий балл: {score.total_score}/200*\n"
                f"───────────────────\n"
                f"💰 *Цена:* {price.price:,} {price.currency}\n"
                f"📉 *Скидка от рынка:* {score.discount_pct}%" if score.discount_pct else "N/A"
                f"\n📐 *Площадь:* {detail.total_area} м² ({detail.rooms_count}-комн)\n"
                f"🏢 *Этаж:* {detail.floor}/{detail.floors_count}\n"
                f"🚇 *Метро:* {detail.metro_name} ({detail.metro_time} мин {detail.metro_transport})\n"
                f"📍 *Адрес:* {address}\n"
                f"───────────────────\n"
                f"✨ *Качество:* {score.quality_score}/100\n"
                f"🔥 *Интерес:* {score.market_interest_score}/100\n"
                f"───────────────────\n"
                f"🌐 [Посмотреть на Cian]({offer.url})\n"
            )

            # Send to all active users
            for user in active_users:
                try:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=message_text,
                        parse_mode="Markdown",
                        disable_web_page_preview=False
                    )
                    logger.info(f"✅ Notification sent to user {user.telegram_id} for offer {offer.cian_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to send notification to user {user.telegram_id}: {e}")

            # Mark as notified
            score.is_notified = True
            db.commit()

    except Exception as e:
        logger.error(f"❌ Error in send_high_score_notifications: {e}")
        db.rollback()
    finally:
        db.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(send_high_score_notifications())
