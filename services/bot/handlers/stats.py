from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import logging
import services.bot.keyboards as kb
from core.database.apartment_service import ApartmentService
from core.database.notification_service import NotificationService
from services.bot.handlers.common import handle_network_errors, safe_edit_message
from services.bot.handlers.browser import browse_apartments_list_helper

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("stats"))
@handle_network_errors
async def stats_handler(message: Message):
    """Показывает статистику базы данных"""
    try:
        stats = await ApartmentService.get_statistics()
        
        response = f"""📊 **Статистика базы данных:**

📈 Всего объявлений: {stats['total_apartments']}
✅ Активных: {stats['active_apartments']}
❌ Неактивных: {stats['inactive_apartments']}
💰 Средняя цена: {stats['average_price']:,} ₽"""
        
        await message.answer(response, parse_mode="Markdown")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении статистики: {str(e)}")

@router.message(Command("recent"))  
@handle_network_errors
async def recent_handler(message: Message):
    """Показывает недавно добавленные объявления"""
    try:
        from core.database.models import async_session, Apartment
        from sqlalchemy import select, and_
        from datetime import datetime, timedelta
        
        since_date = datetime.utcnow() - timedelta(days=7)
        
        async with async_session() as session:
            query = select(Apartment).where(
                and_(
                    Apartment.first_seen >= since_date,
                    Apartment.is_active == True
                )
            ).order_by(Apartment.first_seen.desc()).limit(5)
            
            result = await session.execute(query)
            apartments = result.scalars().all()
        
        if not apartments:
            await message.answer("📭 Новых объявлений не найдено")
            return
        
        response = f"🆕 **Новые объявления ({len(apartments)}):**\n\n"
        
        for apt in apartments:
            price_str = f"{apt.price:,} ₽" if apt.price else "цена не указана"
            date_str = apt.first_seen.strftime("%d.%m.%Y")
            
            response += f"**{date_str} - {price_str}**\n"
            response += f"{apt.title[:60]}...\n"
            response += f"🔗 [Посмотреть]({apt.url})\n\n"
        
        await message.answer(response, parse_mode="Markdown", disable_web_page_preview=True)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении недавних объявлений: {str(e)}")

@router.callback_query(F.data == "stats") 
@handle_network_errors
async def stats_callback_handler(callback: CallbackQuery):
    """Статистика через кнопку"""
    try:
        stats = await ApartmentService.get_statistics()
        
        response = f"""📊 **Статистика базы данных:**

📈 Всего объявлений: {stats['total_apartments']}
✅ Активных: {stats['active_apartments']}
❌ Неактивных: {stats['inactive_apartments']}
💰 Средняя цена: {stats['average_price']:,} ₽"""
        
        await safe_edit_message(callback, response, parse_mode="Markdown", reply_markup=kb.back_to_menu)
        
    except Exception as e:
        logger.error(f"Error in stats_callback_handler: {e}")
        await safe_edit_message(callback, f"❌ Ошибка при получении статистики: {str(e)}", reply_markup=kb.back_to_menu)


@router.callback_query(F.data == "recent")
@handle_network_errors
async def recent_callback_handler(callback: CallbackQuery):
    """Новые квартиры для пользователя в плеере"""
    try:
        user_id = callback.from_user.id
        
        # Отмечаем уведомления как прочитанные
        await NotificationService.mark_notifications_read(user_id)
        
        # Запускаем плеер для новых квартир
        # Circular import issue: browser imports stats? No.
        # But we need browse_apartments_list_helper here.
        # Check browser.py content - it is not created yet.
        # I will create browser.py next, and then ensure stats imports form browser.
        # Wait, stats.py imports browser? Yes.
        # browser.py does NOT import stats.
        # So stats -> browser is OK.
        
        await browse_apartments_list_helper(callback, index=0, list_context="new")
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in recent_callback_handler: {e}")
        await safe_edit_message(callback, f"❌ Ошибка при получении новых квартир: {str(e)}", reply_markup=kb.back_to_menu)
