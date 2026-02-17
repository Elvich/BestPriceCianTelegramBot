import asyncio
import logging
import os
import sys
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from dotenv import load_dotenv
from sqlalchemy import text, desc, func

# Add the project root to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.core.database import SessionLocal, User, Offer, OfferDetail, OfferScore, OfferPrice
from src.bot.keyboards import get_main_keyboard, get_offer_inline_keyboard

# Load environment variables
load_dotenv(os.path.join(project_root, ".env"))

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN or TOKEN == "your_bot_token_here":
    print("❌ Error: TELEGRAM_BOT_TOKEN not found in .env or is a placeholder.")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize bot and dispatcher
bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- Helper Functions ---

async def register_user(message: Message):
    """Register or update user in the database"""
    tg_user = message.from_user
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == tg_user.id).first()
        is_developer = False
        
        if not user:
            user = User(
                telegram_id=tg_user.id,
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                is_active=True
            )
            db.add(user)
            logger.info(f"🆕 New user registered: {tg_user.id} (@{tg_user.username})")
            welcome_msg = f"Привет, {tg_user.first_name}! Ты успешно зарегистрирован."
        else:
            user.last_activity_at = datetime.now()
            user.username = tg_user.username
            user.first_name = tg_user.first_name
            user.last_name = tg_user.last_name
            is_developer = user.is_developer
            logger.info(f"👤 User active: {tg_user.id} (@{tg_user.username})")
            welcome_msg = f"С возвращением, {tg_user.first_name}!"
            
        db.commit()
        return welcome_msg, is_developer
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        db.rollback()
        return "Произошла ошибка при регистрации. Попробуй позже.", False
    finally:
        db.close()

from sqlalchemy import and_, not_, exists
from src.core.database import SessionLocal, User, Offer, OfferDetail, OfferScore, OfferPrice, UserInteraction, OfferStat, BannedMetro

async def get_offer_data(index: int, user_tg_id: int, only_favorites: bool = False, sort_by: str = "score"):
    """Fetch offer data filtered by user interactions and sorted by preferred metric"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_tg_id).first()
        if not user:
            return None, 0
            
        # Base filters
        disliked_ids = db.query(UserInteraction.offer_id).filter(
            UserInteraction.user_id == user.id,
            UserInteraction.interaction_type == 'dislike'
        ).subquery()
        
        liked_ids = db.query(UserInteraction.offer_id).filter(
            UserInteraction.user_id == user.id,
            UserInteraction.interaction_type == 'like'
        ).subquery()

        # Banned metros subquery
        banned_metros = db.query(BannedMetro.name).subquery()
        
        # Base query to count total offers that HAVE SCORES and ARE NOT BANNED
        base_offers_query = (
            db.query(Offer.id)
            .join(OfferScore, Offer.id == OfferScore.offer_id)
            .join(OfferDetail, Offer.id == OfferDetail.offer_id)
            .filter(not_(Offer.id.in_(disliked_ids)))
            .filter(not_(OfferDetail.metro_name.in_(banned_metros)))
        )
        if only_favorites:
            base_offers_query = base_offers_query.filter(Offer.id.in_(liked_ids))
            
        count = base_offers_query.count()
        if count == 0:
            return None, 0
        
        index = index % count
        
        # Subquery to get the latest price for each offer
        latest_price_sub = (
            db.query(
                OfferPrice.offer_id, 
                func.max(OfferPrice.scraped_at).label('max_scraped')
            )
            .group_by(OfferPrice.offer_id)
            .subquery()
        )

        # Subquery for latest stats (views)
        latest_stats_sub = (
            db.query(
                OfferStat.offer_id,
                func.max(OfferStat.scraped_at).label('max_scraped')
            )
            .group_by(OfferStat.offer_id)
            .subquery()
        )
        
        # Main query for data
        query = (
            db.query(Offer, OfferDetail, OfferScore, OfferPrice, OfferStat)
            .join(OfferDetail, Offer.id == OfferDetail.offer_id)
            .join(OfferScore, Offer.id == OfferScore.offer_id)
            .join(OfferPrice, Offer.id == OfferPrice.offer_id)
            .join(
                latest_price_sub,
                (OfferPrice.offer_id == latest_price_sub.c.offer_id) & 
                (OfferPrice.scraped_at == latest_price_sub.c.max_scraped)
            )
            .outerjoin(latest_stats_sub, Offer.id == latest_stats_sub.c.offer_id)
            .outerjoin(
                OfferStat,
                (OfferStat.offer_id == latest_stats_sub.c.offer_id) & 
                (OfferStat.scraped_at == latest_stats_sub.c.max_scraped)
            )
            .filter(Offer.id.in_(base_offers_query.subquery()))
        )
        
        if only_favorites:
            query = query.filter(Offer.id.in_(liked_ids))

        # Sorting
        if sort_by == "views":
            query = query.order_by(desc(func.coalesce(OfferStat.views_today, 0)), Offer.id)
        else: # score
            query = query.order_by(desc(OfferScore.total_score), Offer.id)
            
        result = (
            query.offset(index)
            .limit(1)
            .first()
        )
        
        if not result:
            return None, count
            
        offer, detail, score, price, stat = result
        
        # Check if is favorite
        is_favorite = db.query(UserInteraction).filter(
            UserInteraction.user_id == user.id,
            UserInteraction.offer_id == offer.id,
            UserInteraction.interaction_type == 'like'
        ).first() is not None
        
        address = "Адрес не указан"
        if detail.extra_attributes and isinstance(detail.extra_attributes, dict):
            address = detail.extra_attributes.get('address', address)
            
        prefix = "❤️ *ИЗБРАННОЕ*" if only_favorites else "🏠 *Объявление*"
        views_today = stat.views_today if stat else 0
        
        text = (
            f"{prefix} {index + 1}/{count}\n"
            f"🎯 *Общий балл: {score.total_score}/200*\n"
            f"👁️ *Просмотров:* {views_today} за день\n"
            f"───────────────────\n"
            f"🌐 *Ссылка:* {offer.url}\n"
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
            f"🌐 *Ссылка:* {offer.url}\n"
        )
        
        return {
            "text": text, 
            "url": offer.url, 
            "id": offer.id,
            "index": index, 
            "total": count, 
            "is_favorite": is_favorite,
            "sort_by": sort_by,
            "mode": "favorites" if only_favorites else "all"
        }, count
    finally:
        db.close()

# --- Handlers ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    """Handle /start command"""
    welcome_msg, is_developer = await register_user(message)
    
    response = f"{welcome_msg}\n\nЯ помогу тебе найти лучшие предложения на квартиры!"
    if is_developer:
        response += "\n\n👨‍💻 *Режим разработчика активирован.*"
        
    await message.answer(
        response, 
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(is_developer)
    )

@dp.message(F.text == "🔍 Обзор объявлений")
async def handle_browse(message: Message):
    """Handle Browse button"""
    data, count = await get_offer_data(0, message.from_user.id, only_favorites=False, sort_by="score")
    
    if not data:
        await message.answer("😔 В базе пока нет новых объявлений для тебя. Попробуй позже!")
        return
        
    await message.answer(
        data["text"],
        reply_markup=get_offer_inline_keyboard(data["id"], data["url"], 0, count, data["is_favorite"], data["sort_by"]),
        parse_mode="Markdown"
    )

@dp.message(F.text == "❤️ Избранное")
async def handle_favorites(message: Message):
    """Handle Favorites button"""
    data, count = await get_offer_data(0, message.from_user.id, only_favorites=True, sort_by="score")
    
    if not data:
        await message.answer("❤️ У тебя пока нет избранных объявлений. Ставь лайки при просмотре!")
        return
        
    await message.answer(
        data["text"],
        reply_markup=get_offer_inline_keyboard(data["id"], data["url"], 0, count, data["is_favorite"], data["sort_by"]),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("browse:"))
async def process_browse_callback(callback: CallbackQuery):
    """Handle carousel navigation"""
    parts = callback.data.split(":")
    index = int(parts[1])
    sort_by = parts[2] if len(parts) > 2 else "score"
    
    # Determine mode from the current message text
    only_favorites = "ИЗБРАННОЕ" in callback.message.text
    
    data, count = await get_offer_data(index, callback.from_user.id, only_favorites=only_favorites, sort_by=sort_by)
    
    if not data:
        await callback.answer("Ошибка: Данные не найдены")
        return

    try:
        await callback.message.edit_text(
            data["text"],
            reply_markup=get_offer_inline_keyboard(data["id"], data["url"], index, count, data["is_favorite"], sort_by),
            parse_mode="Markdown"
        )
    except TelegramBadRequest:
        pass
    
    await callback.answer()

@dp.callback_query(F.data.startswith("sort:"))
async def process_sort_toggle(callback: CallbackQuery):
    """Handle sort toggle"""
    parts = callback.data.split(":")
    new_sort = parts[1]
    current_index = int(parts[2])
    
    only_favorites = "ИЗБРАННОЕ" in callback.message.text
    
    # When changing sort, we reset to index 0 for better UX? Or keep index?
    # Keeping index might show a completely different apartment.
    # Resetting to 0 is usually what users expect when changing search/sort.
    data, count = await get_offer_data(0, callback.from_user.id, only_favorites=only_favorites, sort_by=new_sort)
    
    if not data:
        await callback.answer("Ошибка: Нет данных")
        return

    await callback.message.edit_text(
        data["text"],
        reply_markup=get_offer_inline_keyboard(data["id"], data["url"], 0, count, data["is_favorite"], new_sort),
        parse_mode="Markdown"
    )
    await callback.answer(f"Сортировка: {'Баллы' if new_sort == 'score' else 'Просмотры'}")

@dp.callback_query(F.data.startswith("interact:"))
async def process_interaction(callback: CallbackQuery):
    """Handle Like/Dislike interactions"""
    parts = callback.data.split(":")
    action = parts[1]
    offer_id = int(parts[2])
    current_index = int(parts[3]) if len(parts) > 3 else 0
    sort_by = parts[4] if len(parts) > 4 else "score"
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            return
            
        existing = db.query(UserInteraction).filter(
            UserInteraction.user_id == user.id,
            UserInteraction.offer_id == offer_id
        ).first()
        
        if existing:
            if action == 'like' and existing.interaction_type == 'like':
                # Toggle off favorite
                db.delete(existing)
                msg = "💔 Удалено из избранного"
            else:
                existing.interaction_type = action
                msg = "❤️ Добавлено в избранное" if action == 'like' else "👎 Пропущено (скрыто)"
        else:
            interaction = UserInteraction(
                user_id=user.id,
                offer_id=offer_id,
                interaction_type=action
            )
            db.add(interaction)
            msg = "❤️ Добавлено в избранное" if action == 'like' else "👎 Пропущено (скрыто)"
            
        db.commit()
        await callback.answer(msg)
        
        only_favorites = "ИЗБРАННОЕ" in callback.message.text
        
        if action == 'dislike':
            # Auto-move to next if disliked
            data, count = await get_offer_data(current_index, callback.from_user.id, only_favorites=only_favorites, sort_by=sort_by)
            if not data:
                await callback.message.delete()
                await callback.message.answer("🎉 Ого! Ты просмотрел всё, что было!")
                return
        else:
            # Refresh current for Like toggle
            data, count = await get_offer_data(current_index, callback.from_user.id, only_favorites=only_favorites, sort_by=sort_by)
            
        await callback.message.edit_text(
            data["text"],
            reply_markup=get_offer_inline_keyboard(data["id"], data["url"], data["index"], count, data["is_favorite"], sort_by),
            parse_mode="Markdown"
        )
        
    except Exception as e:
        logger.error(f"Interaction error: {e}")
        db.rollback()
        await callback.answer("Ошибка сохранения")
    finally:
        db.close()

# --- Developer Handlers ---

@dp.message(F.text == "📊 Статистика")
async def handle_stats(message: Message):
    """Handle Stats button (Developer only)"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        if not (user and user.is_developer):
            return

        stats_query = text("""
            SELECT 
                COUNT(*) as total_offers,
                ROUND(AVG(total_score)::numeric, 1) as avg_score,
                COUNT(CASE WHEN total_score >= 160 THEN 1 END) as top_tier,
                COUNT(CASE WHEN total_score >= 130 AND total_score < 160 THEN 1 END) as high_tier,
                COUNT(CASE WHEN total_score >= 100 AND total_score < 130 THEN 1 END) as mid_tier,
                COUNT(CASE WHEN total_score < 100 THEN 1 END) as low_tier
            FROM offer_scores
        """)
        
        result = db.execute(stats_query).fetchone()
        
        if result and result[0] > 0:
            report = (
                "📊 *СТАТИСТИКА РЫНКА*\n"
                "───────────────────\n"
                f"🏘 Всего оценено: *{result[0]}*\n"
                f"⭐ Средний балл: *{result[1]}*\n"
                "───────────────────\n"
                "📈 *РАСПРЕДЕЛЕНИЕ:*\n"
                f"🔥🔥🔥 Топ (160-200): *{result[2]}*\n"
                f"🔥 Высокий балл (130-159): *{result[3]}*\n"
                f"⭐ Средний балл (100-129): *{result[4]}*\n"
                f"✅ Низкий балл (<100): *{result[5]}*\n"
            )
            await message.answer(report, parse_mode="Markdown")
        else:
            await message.answer("📈 Статистика пока недоступна. Нужно собрать больше данных!")
    finally:
        db.close()

@dp.message(F.text == "🔗 Управление URL")
async def handle_manage_urls(message: Message):
    """Handle Manage URLs button (Developer only)"""
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    db.close()
    
    if not (user and user.is_developer):
        return
        
    await message.answer("⚙️ Меню управления источниками Cian. (В разработке)")

@dp.message(F.text == "🚀 Запуск парсера")
async def handle_run_parser(message: Message):
    """Handle Run Parser button (Developer only)"""
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
    db.close()
    
    if not (user and user.is_developer):
        return
        
    await message.answer("⚡ Парсер запущен в фоновом режиме. Я сообщу о результатах!")

# --- Main ---

async def main():
    logger.info("🚀 Starting bot...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped.")
