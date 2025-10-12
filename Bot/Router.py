from aiogram import Router, F 
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramNetworkError, TelegramBadRequest
from . import kb
import sys
import os
import logging
from functools import wraps
import asyncio
from .error_handlers import network_retry, RetryConfig, NetworkMonitor

# Добавляем путь к родительской директории
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from DB.apartment_service import ApartmentService
from utils.excel_exporter import ExcelExporter

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

# Конфигурация для повторных попыток
RETRY_CONFIG = RetryConfig(max_retries=3, base_delay=1.0, exponential_backoff=True)

# Декоратор для обработки сетевых ошибок
def handle_network_errors(func):
    @wraps(func)
    @network_retry(config=RETRY_CONFIG)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            
            # Попытаемся уведомить пользователя о проблеме
            try:
                if args and hasattr(args[0], 'answer'):
                    await args[0].answer("❌ Произошла ошибка. Попробуйте позже.")
                elif args and hasattr(args[0], 'message') and hasattr(args[0].message, 'answer'):
                    await args[0].message.answer("❌ Произошла ошибка. Попробуйте позже.")
            except:
                pass  # Если не удается отправить сообщение, просто игнорируем
            
            raise e  # Пробрасываем ошибку дальше
    return wrapper

# Функция для безопасного редактирования сообщений
async def safe_edit_message(callback, text, **kwargs):
    """Безопасное редактирование сообщения с проверкой на дублирование контента"""
    try:
        # Проверяем, изменился ли текст сообщения
        if hasattr(callback.message, 'text') and callback.message.text == text:
            # Если текст не изменился, просто отвечаем на callback
            await callback.answer()
            return
        
        await callback.message.edit_text(text, **kwargs)
    except TelegramBadRequest as e:
        if "message is not modified" in str(e).lower():
            # Сообщение не изменилось, просто отвечаем на callback
            await callback.answer()
        else:
            # Другая ошибка, пробуем отправить новое сообщение
            await callback.message.answer(text, **kwargs)
    except Exception as e:
        logger.error(f"Error in safe_edit_message: {e}")
        await callback.answer("❌ Ошибка при обновлении сообщения")

@router.message(CommandStart())
@handle_network_errors
async def command_start_handler(message: Message, state: FSMContext):
    await message.answer(
        text=f"""Привет, {message.from_user.full_name}! 🏠

Я бот для поиска квартир на Циан по выгодным ценам.

Доступные команды:
🔍 /search - Поиск квартир
📊 /stats - Статистика базы данных
🚇 /metro - Список станций метро
🆕 /recent - Недавно добавленные объявления
📄 /export - Экспорт данных в Excel

Для начала попробуйте команду /search""", 
        reply_markup=kb.main_menu
    )

@router.message(Command("search"))
@handle_network_errors
async def search_apartments_handler(message: Message, state: FSMContext):
    """Обработчик команды поиска квартир"""
    await search_apartments_helper(message)

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

@router.message(Command("metro"))
@handle_network_errors
async def metro_handler(message: Message):
    """Показывает список станций метро"""
    try:
        from DB.models import async_session, MetroStation
        from sqlalchemy import select
        
        async with async_session() as session:
            query = select(MetroStation.station_name).distinct().order_by(MetroStation.station_name)
            result = await session.execute(query)
            stations = result.scalars().all()
        
        if not stations:
            await message.answer("❌ Станции метро не найдены")
            return
        
        response = f"🚇 **Станции метро в базе ({len(stations)}):**\n\n"
        response += "\n".join([f"• {station}" for station in stations])
        
        await message.answer(response, parse_mode="Markdown")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении списка станций: {str(e)}")

@router.message(Command("recent"))  
@handle_network_errors
async def recent_handler(message: Message):
    """Показывает недавно добавленные объявления"""
    try:
        from DB.models import async_session, Apartment
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
            await message.answer("📭 Новых объявлений за последние 7 дней не найдено")
            return
        
        response = f"🆕 **Новые объявления за неделю ({len(apartments)}):**\n\n"
        
        for apt in apartments:
            price_str = f"{apt.price:,} ₽" if apt.price else "цена не указана"
            date_str = apt.first_seen.strftime("%d.%m.%Y")
            
            response += f"**{date_str} - {price_str}**\n"
            response += f"{apt.title[:60]}...\n"
            response += f"🔗 [Посмотреть]({apt.url})\n\n"
        
        await message.answer(response, parse_mode="Markdown", disable_web_page_preview=True)
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при получении недавних объявлений: {str(e)}")

@router.callback_query(F.data == "help")
@handle_network_errors
async def help_callback_handler(callback: CallbackQuery):
    """Обработчик кнопки помощи"""
    help_text = """ℹ️ **Справка по боту**

**Доступные команды:**
🔍 /search - Поиск самых выгодных квартир
📊 /stats - Статистика базы данных  
🚇 /metro - Список доступных станций метро
🆕 /recent - Недавно добавленные объявления
📄 /export - Экспорт данных в Excel формат

**Как это работает:**
Бот парсит объявления с Cian.ru и сохраняет их в базу данных. Вы можете искать квартиры по различным критериям и отслеживать изменения цен.

**Возможности:**
• Поиск без дублирования объявлений
• Отслеживание истории изменения цен
• Информация о близости к станциям метро
• Фильтрация по цене и локации
• Экспорт данных в Excel с красивым оформлением"""

    await safe_edit_message(callback, help_text, parse_mode="Markdown", reply_markup=kb.back_to_menu)

@router.callback_query(F.data == "back_to_menu")
@handle_network_errors
async def back_to_menu_handler(callback: CallbackQuery):
    """Возврат в главное меню"""
    text = f"""Привет, {callback.from_user.full_name}! 🏠

Я бот для поиска квартир на Циан по выгодным ценам.

Используйте кнопки ниже или команды:
🔍 /search - Поиск квартир
📊 /stats - Статистика  
🚇 /metro - Станции метро"""
    
    await safe_edit_message(callback, text, reply_markup=kb.main_menu)

# Обработчики кнопок главного меню
@router.callback_query(F.data == "search")
@handle_network_errors
async def search_callback_handler(callback: CallbackQuery):
    """Поиск через кнопку"""
    # Создаем фиктивное сообщение для использования логики команды /search
    message = callback.message
    await search_apartments_helper(message, is_callback=True)
    await callback.answer()

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

@router.callback_query(F.data == "metro")
@handle_network_errors
async def metro_callback_handler(callback: CallbackQuery):
    """Станции метро через кнопку"""
    try:
        from DB.models import async_session, MetroStation
        from sqlalchemy import select
        
        async with async_session() as session:
            query = select(MetroStation.station_name).distinct().order_by(MetroStation.station_name)
            result = await session.execute(query)
            stations = result.scalars().all()
        
        if not stations:
            await safe_edit_message(callback, "❌ Станции метро не найдены", reply_markup=kb.back_to_menu)
            return
        
        response = f"🚇 **Станции метро в базе ({len(stations)}):**\n\n"
        # Ограничиваем количество станций, чтобы не превысить лимит сообщения
        stations_text = "\n".join([f"• {station}" for station in stations[:20]])
        response += stations_text
        
        if len(stations) > 20:
            response += f"\n\n... и еще {len(stations) - 20} станций"
        
        await safe_edit_message(callback, response, parse_mode="Markdown", reply_markup=kb.back_to_menu)
        
    except Exception as e:
        logger.error(f"Error in metro_callback_handler: {e}")
        await safe_edit_message(callback, f"❌ Ошибка при получении списка станций: {str(e)}", reply_markup=kb.back_to_menu)

@router.callback_query(F.data == "recent")
@handle_network_errors
async def recent_callback_handler(callback: CallbackQuery):
    """Недавние объявления через кнопку"""
    try:
        from DB.models import async_session, Apartment
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
            await safe_edit_message(callback, "📭 Новых объявлений за последние 7 дней не найдено", reply_markup=kb.back_to_menu)
            return
        
        response = f"🆕 **Новые объявления за неделю ({len(apartments)}):**\n\n"
        
        for apt in apartments:
            price_str = f"{apt.price:,} ₽" if apt.price else "цена не указана"
            date_str = apt.first_seen.strftime("%d.%m.%Y")
            
            response += f"**{date_str} - {price_str}**\n"
            response += f"{apt.title[:50]}...\n"
            response += f"🔗 [Посмотреть]({apt.url})\n\n"
        
        await safe_edit_message(callback, response, parse_mode="Markdown", reply_markup=kb.back_to_menu, disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error in recent_callback_handler: {e}")
        await safe_edit_message(callback, f"❌ Ошибка при получении недавних объявлений: {str(e)}", reply_markup=kb.back_to_menu)

# Вспомогательная функция для поиска
async def search_apartments_helper(message, is_callback=False):
    """Вспомогательная функция для логики поиска"""
    try:
        apartments = await ApartmentService.get_apartments(limit=5, only_active=True, only_production=True)
        
        if not apartments:
            text = "❌ Объявления не найдены. Возможно, база данных пуста."
            if is_callback:
                # Создаем фиктивный callback для использования safe_edit_message
                class FakeCallback:
                    def __init__(self, message):
                        self.message = message
                    async def answer(self):
                        pass
                await safe_edit_message(FakeCallback(message), text, reply_markup=kb.back_to_menu)
            else:
                await message.answer(text)
            return
        
        response = "🔍 **Топ-5 самых выгодных предложений:**\n\n"
        
        for i, apt in enumerate(apartments, 1):
            price_str = f"{apt.price:,} ₽" if apt.price else "цена не указана"
            price_per_sqm_str = f" ({apt.price_per_sqm:,} ₽/м²)" if apt.price_per_sqm else ""
            
            metro_info = []
            for metro in apt.metro_stations[:2]:
                metro_info.append(f"{metro.station_name} {metro.travel_time}")
            metro_str = f"\n🚇 {', '.join(metro_info)}" if metro_info else ""
            
            address_str = f"\n📍 {apt.address}" if apt.address else ""
            
            response += f"**{i}. {price_str}{price_per_sqm_str}**\n"
            response += f"{apt.title}\n"
            response += f"🔗 [Посмотреть на Cian]({apt.url})"
            response += metro_str
            response += address_str
            response += "\n\n"
        
        if is_callback:
            class FakeCallback:
                def __init__(self, message):
                    self.message = message
                async def answer(self):
                    pass
            await safe_edit_message(FakeCallback(message), response, parse_mode="Markdown", reply_markup=kb.back_to_menu, disable_web_page_preview=True)
        else:
            await message.answer(response, parse_mode="Markdown", disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error in search_apartments_helper: {e}")
        error_text = f"❌ Ошибка при поиске: {str(e)}"
        if is_callback:
            class FakeCallback:
                def __init__(self, message):
                    self.message = message
                async def answer(self):
                    pass
            await safe_edit_message(FakeCallback(message), error_text, reply_markup=kb.back_to_menu)
        else:
            await message.answer(error_text)

# Обработчики экспорта данных
@router.message(Command("export"))
@handle_network_errors
async def export_command_handler(message: Message):
    """Команда экспорта данных"""
    await message.answer(
        "📄 **Экспорт данных в Excel**\n\nВыберите тип экспорта:",
        parse_mode="Markdown",
        reply_markup=kb.export_menu
    )

@router.callback_query(F.data == "export_menu")
@handle_network_errors
async def export_menu_handler(callback: CallbackQuery):
    """Показывает меню экспорта"""
    await safe_edit_message(callback, "📄 **Экспорт данных в Excel**\n\nВыберите тип экспорта:", parse_mode="Markdown", reply_markup=kb.export_menu)

@router.callback_query(F.data == "export_all")
@handle_network_errors
async def export_all_handler(callback: CallbackQuery):
    """Экспорт всех объявлений"""
    await callback.answer("⏳ Создаем Excel файл...", show_alert=True)
    
    try:
        # Показываем сообщение о процессе
        await safe_edit_message(callback, "⏳ **Создание Excel файла...**\n\nПожалуйста, подождите. Это может занять некоторое время.", parse_mode="Markdown")
        
        # Создаем Excel файл
        file_path = await ExcelExporter.export_apartments_to_excel(limit=500)  # Ограничиваем до 500 для Telegram
        
        # Отправляем файл
        from aiogram.types import FSInputFile
        document = FSInputFile(file_path)
        
        await callback.message.answer_document(
            document=document,
            caption="📋 **Все объявления о квартирах**\n\nВ файле содержатся активные объявления с подробной информацией.",
            parse_mode="Markdown"
        )
        
        # Удаляем временный файл
        os.remove(file_path)
        
        # Возвращаемся в меню экспорта
        await safe_edit_message(callback, "✅ **Файл успешно создан и отправлен!**\n\nВыберите другой тип экспорта или вернитесь в главное меню:", parse_mode="Markdown", reply_markup=kb.export_menu)
        
    except Exception as e:
        logger.error(f"Error in export_all_handler: {e}")
        await safe_edit_message(callback, f"❌ **Ошибка при создании файла:**\n{str(e)}", parse_mode="Markdown", reply_markup=kb.export_menu)

@router.callback_query(F.data == "export_cheap")
@handle_network_errors
async def export_cheap_handler(callback: CallbackQuery):
    """Экспорт дешевых квартир (до 15 млн)"""
    await callback.answer("⏳ Создаем Excel файл...", show_alert=True)
    
    try:
        await safe_edit_message(callback, "⏳ **Создание Excel файла с дешевыми квартирами...**\n\nПожалуйста, подождите.", parse_mode="Markdown")
        
        file_path = await ExcelExporter.export_apartments_to_excel(
            max_price=20000000,
            limit=500
        )
        
        from aiogram.types import FSInputFile
        document = FSInputFile(file_path)
        
        await callback.message.answer_document(
            document=document,
            caption="💰 **Квартиры до 20 млн рублей**\n\nВ файле содержатся самые выгодные предложения.",
            parse_mode="Markdown"
        )
        
        os.remove(file_path)
        
        await safe_edit_message(callback, "✅ **Файл с дешевыми квартирами отправлен!**\n\nВыберите другой тип экспорта:", parse_mode="Markdown", reply_markup=kb.export_menu)
        
    except Exception as e:
        logger.error(f"Error in export_cheap_handler: {e}")
        await safe_edit_message(callback, f"❌ **Ошибка при создании файла:**\n{str(e)}", parse_mode="Markdown", reply_markup=kb.export_menu)

@router.callback_query(F.data == "export_stats")
@handle_network_errors
async def export_stats_handler(callback: CallbackQuery):
    """Экспорт статистики"""
    await callback.answer("⏳ Создаем статистику...", show_alert=True)
    
    try:
        await safe_edit_message(callback, "⏳ **Создание статистического отчета...**\n\nПожалуйста, подождите.", parse_mode="Markdown")
        
        file_path = await ExcelExporter.export_statistics_to_excel()
        
        from aiogram.types import FSInputFile
        document = FSInputFile(file_path)
        
        await callback.message.answer_document(
            document=document,
            caption="📊 **Статистический отчет**\n\nВ файле содержится общая статистика и топ дешевых квартир.",
            parse_mode="Markdown"
        )
        
        os.remove(file_path)
        
        await safe_edit_message(callback, "✅ **Статистика отправлена!**\n\nВыберите другой тип экспорта:", parse_mode="Markdown", reply_markup=kb.export_menu)
        
    except Exception as e:
        logger.error(f"Error in export_stats_handler: {e}")
        await safe_edit_message(callback, f"❌ **Ошибка при создании статистики:**\n{str(e)}", parse_mode="Markdown", reply_markup=kb.export_menu)

@router.callback_query(F.data == "export_top50")
@handle_network_errors
async def export_top50_handler(callback: CallbackQuery):
    """Экспорт топ-50 дешевых квартир"""
    await callback.answer("⏳ Создаем топ-50...", show_alert=True)
    
    try:
        await safe_edit_message(callback, "⏳ **Создание топ-50 дешевых квартир...**\n\nПожалуйста, подождите.", parse_mode="Markdown")
        
        file_path = await ExcelExporter.export_apartments_to_excel(limit=50)
        
        from aiogram.types import FSInputFile
        document = FSInputFile(file_path)
        
        await callback.message.answer_document(
            document=document,
            caption="🎯 **Топ-50 самых дешевых квартир**\n\nВ файле содержатся лучшие предложения по цене.",
            parse_mode="Markdown"
        )
        
        os.remove(file_path)
        
        await safe_edit_message(callback, "✅ **Топ-50 дешевых квартир отправлен!**\n\nВыберите другой тип экспорта:", parse_mode="Markdown", reply_markup=kb.export_menu)
        
    except Exception as e:
        logger.error(f"Error in export_top50_handler: {e}")
        await safe_edit_message(callback, f"❌ **Ошибка при создании топ-50:**\n{str(e)}", parse_mode="Markdown", reply_markup=kb.export_menu)
    