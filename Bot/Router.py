from aiogram import Router, F 
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramNetworkError, TelegramBadRequest
import Kb as kb
import sys
import os
import logging
from functools import wraps
import asyncio
from error_handlers import network_retry, RetryConfig, NetworkMonitor

# Добавляем путь к родительской директории
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from DB.apartment_service import ApartmentService
from DB.notification_service import NotificationService
from DB.user_service import UserService
from DB.reaction_service import ReactionService
from utils.excel_exporter import ExcelExporter
from notification_sender import NotificationSender

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

# Конфигурация для повторных попыток
RETRY_CONFIG = RetryConfig(max_retries=3, base_delay=1.0, exponential_backoff=True)

# Декоратор для обработки сетевых ошибок и автоматического создания пользователей
def handle_network_errors(func):
    @wraps(func)
    @network_retry(config=RETRY_CONFIG)
    async def wrapper(*args, **kwargs):
        try:
            # Автоматически создаем/обновляем пользователя при каждом взаимодействии
            user_obj = None
            if args:
                if hasattr(args[0], 'from_user'):  # Message или CallbackQuery
                    user = args[0].from_user
                    user_obj = await UserService.get_or_create_user(
                        telegram_id=user.id,
                        username=user.username,
                        first_name=user.first_name,
                        last_name=user.last_name
                    )
                    
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
    user_id = message.from_user.id
    
    # Отмечаем уведомления как прочитанные при входе в бота
    await NotificationService.mark_notifications_read(user_id)
    
    # Проверяем есть ли новые квартиры
    new_count = len(await NotificationService.get_new_apartments_for_user(user_id, limit=1))
    new_indicator = f"\n\n🆕 У вас есть {new_count} новых квартир!" if new_count > 0 else ""
    
    await message.answer(
        text=f"""Привет, {message.from_user.full_name}! 🏠

Я бот для поиска квартир на Циан по выгодным ценам.

📱 **Система уведомлений активна!**
Как только появятся новые выгодные квартиры, вы получите уведомление.

Доступные команды:
🔍 /search - Поиск квартир
📊 /stats - Статистика базы данных
🚇 /metro - Список станций метро
🆕 /recent - Новые квартиры для вас
❤️ /liked - Ваши лайки
👎 /disliked - Скрытые квартиры
📄 /export - Экспорт данных в Excel

Для начала попробуйте команду /search{new_indicator}""", 
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
        from DB.Models import async_session, MetroStation
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
        from DB.Models import async_session, Apartment
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
❤️ /liked - Ваши любимые квартиры
👎 /disliked - Скрытые квартиры
�📄 /export - Экспорт данных в Excel формат

**Система лайков и дизлайков:**
❤️ **Лайк** - добавить квартиру в избранное
👎 **Дизлайк** - скрыть из результатов поиска
Нажмите повторно, чтобы отменить реакцию

**Как это работает:**
Бот парсит объявления с Cian.ru и сохраняет их в базу данных. Вы можете искать квартиры по различным критериям и отслеживать изменения цен.

**Возможности:**
• Поиск без дублирования объявлений
• Персональные лайки и дизлайки
• Автоматическое исключение скрытых квартир
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
        from DB.Models import async_session, MetroStation
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
    """Новые квартиры для пользователя (система уведомлений)"""
    try:
        user_id = callback.from_user.id
        
        # Получаем новые квартиры для пользователя
        new_apartments = await NotificationService.get_new_apartments_for_user(user_id, limit=10)
        
        if not new_apartments:
            await safe_edit_message(callback, 
                "📭 Новых квартир пока нет!\n\n"
                "Как только появятся выгодные предложения, вы получите уведомление.",
                reply_markup=kb.back_to_menu)
            return
        
        # Отмечаем уведомления как прочитанные
        await NotificationService.mark_notifications_read(user_id)
        
        response = f"🆕 **Новые квартиры для вас ({len(new_apartments)}):**\n\n"
        
        apartment_ids = []
        for i, apt in enumerate(new_apartments, 1):
            price_str = f"{apt.price:,} ₽" if apt.price else "цена не указана"
            price_per_sqm_str = f" ({apt.price_per_sqm:,} ₽/м²)" if apt.price_per_sqm else ""
            
            # Информация о метро
            metro_info = []
            for metro in apt.metro_stations[:2]:
                metro_info.append(f"{metro.station_name} {metro.travel_time}")
            metro_str = f"\n🚇 {', '.join(metro_info)}" if metro_info else ""
            
            response += f"**{i}. {price_str}{price_per_sqm_str}**\n"
            response += f"{apt.title}\n"
            response += f"🔗 [Посмотреть на Cian]({apt.url})"
            response += metro_str
            response += "\n\n"
            
            apartment_ids.append(apt.id)
        
        # Отмечаем квартиры как просмотренные пользователем
        await NotificationService.mark_apartments_as_viewed(user_id, apartment_ids)
        
        await safe_edit_message(callback, response, parse_mode="Markdown", reply_markup=kb.back_to_menu, disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error in recent_callback_handler: {e}")
        await safe_edit_message(callback, f"❌ Ошибка при получении недавних объявлений: {str(e)}", reply_markup=kb.back_to_menu)

# Вспомогательная функция для поиска
async def search_apartments_helper(message, is_callback=False):
    """Вспомогательная функция для логики поиска"""
    try:
        # Определяем user_id из сообщения
        user_id = None
        if hasattr(message, 'from_user'):
            user_id = message.from_user.id
        elif hasattr(message, 'chat'):
            # Для случаев когда это callback
            user_id = message.chat.id
        
        # Получаем квартиры, исключая дизлайкнутые пользователем
        apartments = await ApartmentService.get_apartments(
            limit=5, 
            only_active=True, 
            only_production=True,
            exclude_disliked_for_user=user_id if user_id else None
        )
        
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
        
        # Отправляем каждую квартиру отдельным сообщением с кнопками реакций
        for i, apt in enumerate(apartments, 1):
            price_str = f"{apt.price:,} ₽" if apt.price else "цена не указана"
            price_per_sqm_str = f" ({apt.price_per_sqm:,} ₽/м²)" if apt.price_per_sqm else ""
            
            metro_info = []
            for metro in apt.metro_stations[:2]:
                metro_info.append(f"{metro.station_name} {metro.travel_time}")
            metro_str = f"\n🚇 {', '.join(metro_info)}" if metro_info else ""
            
            address_str = f"\n📍 {apt.address}" if apt.address else ""
            
            apt_text = f"**{i}. {price_str}{price_per_sqm_str}**\n"
            apt_text += f"{apt.title}\n"
            apt_text += f"🔗 [Посмотреть на Cian]({apt.url})"
            apt_text += metro_str
            apt_text += address_str
            
            # Получаем текущую реакцию пользователя на эту квартиру
            current_reaction = None
            if user_id:
                current_reaction = await ReactionService.get_user_reaction(user_id, apt.id)
            
            # Создаем клавиатуру с кнопками реакций
            reaction_keyboard = kb.create_apartment_reaction_keyboard(apt.id, current_reaction)
            
            # Отправляем квартиру как отдельное сообщение с кнопками
            await message.answer(
                apt_text,
                parse_mode="Markdown",
                reply_markup=reaction_keyboard,
                disable_web_page_preview=True
            )
        
        # Отправляем итоговое сообщение
        final_text = f"✅ Показано {len(apartments)} квартир\n\n"
        final_text += "💡 Используйте кнопки ❤️ и 👎 для лайков/дизлайков\n"
        final_text += "Дизлайкнутые квартиры больше не будут показываться в поиске."
        
        if is_callback:
            class FakeCallback:
                def __init__(self, message):
                    self.message = message
                async def answer(self):
                    pass
            await safe_edit_message(FakeCallback(message), final_text, parse_mode="Markdown", reply_markup=kb.back_to_menu)
        else:
            await message.answer(final_text, parse_mode="Markdown", reply_markup=kb.main_menu)
        
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

# ===== ОБРАБОТЧИКИ РЕАКЦИЙ =====

@router.callback_query(F.data.startswith("reaction_"))
@handle_network_errors
async def reaction_handler(callback: CallbackQuery):
    """Обработчик кнопок лайка/дизлайка"""
    user_id = callback.from_user.id
    
    # Парсим callback_data: "reaction_like_123" или "reaction_dislike_123"
    try:
        parts = callback.data.split('_')
        reaction_type = parts[1]  # 'like' или 'dislike'
        apartment_id = int(parts[2])
    except (IndexError, ValueError):
        await callback.answer("❌ Ошибка в данных", show_alert=True)
        return
    
    try:
        # Переключаем реакцию
        result = await ReactionService.toggle_reaction(user_id, apartment_id, reaction_type)
        
        # Формируем ответ пользователю
        if result['action'] == 'added':
            if reaction_type == 'like':
                message = "❤️ Квартира добавлена в избранное!"
            else:
                message = "👎 Квартира скрыта из результатов поиска"
        elif result['action'] == 'removed':
            if reaction_type == 'like':
                message = "💔 Квартира удалена из избранного"
            else:
                message = "✅ Квартира снова будет показываться"
        elif result['action'] == 'changed':
            if reaction_type == 'like':
                message = "❤️ Изменено на лайк!"
            else:
                message = "👎 Изменено на дизлайк!"
        else:
            message = "✅ Реакция обновлена"
        
        await callback.answer(message, show_alert=True)
        
        # Обновляем клавиатуру с новой реакцией
        new_reaction = result.get('reaction') if result['action'] != 'removed' else None
        new_keyboard = kb.create_apartment_reaction_keyboard(apartment_id, new_reaction)
        
        try:
            await callback.message.edit_reply_markup(reply_markup=new_keyboard)
        except TelegramBadRequest:
            pass  # Игнорируем если сообщение не изменилось
            
    except Exception as e:
        logger.error(f"Error in reaction_handler: {e}")
        await callback.answer("❌ Ошибка при обработке реакции", show_alert=True)

@router.callback_query(F.data == "my_likes")
@handle_network_errors  
async def my_likes_handler(callback: CallbackQuery):
    """Показать лайкнутые квартиры"""
    user_id = callback.from_user.id
    
    try:
        liked_apartments = await ReactionService.get_user_liked_apartments(user_id, limit=10)
        
        if not liked_apartments:
            await safe_edit_message(
                callback,
                "❤️ **Ваши лайки**\n\n"
                "У вас пока нет лайкнутых квартир.\n"
                "Используйте кнопку ❤️ при просмотре квартир, чтобы добавить их в избранное.",
                parse_mode="Markdown",
                reply_markup=kb.back_to_menu
            )
            return
        
        response = "❤️ **Ваши любимые квартиры:**\n\n"
        
        for i, apt in enumerate(liked_apartments, 1):
            price_str = f"{apt.price:,} ₽" if apt.price else "цена не указана"
            price_per_sqm_str = f" ({apt.price_per_sqm:,} ₽/м²)" if apt.price_per_sqm else ""
            
            response += f"**{i}. {price_str}**{price_per_sqm_str}\n"
            response += f"_{apt.title[:80]}{'...' if len(apt.title) > 80 else ''}_\n"
            
            # Добавляем информацию о метро
            metro_info = [station.station_name for station in apt.metro_stations[:2]]
            metro_str = f"🚇 {', '.join(metro_info)}" if metro_info else ""
            if metro_str:
                response += f"{metro_str}\n"
            
            response += f"[Открыть на Cian]({apt.url})\n\n"
            
            if len(response) > 3500:  # Ограничиваем размер сообщения
                response += "...\n\n"
                break
        
        # Показываем статистику
        summary = await ReactionService.get_user_reactions_summary(user_id)
        response += f"📊 Всего лайков: {summary['likes']}"
        
        await safe_edit_message(
            callback,
            response,
            parse_mode="Markdown",
            reply_markup=kb.back_to_menu,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error in my_likes_handler: {e}")
        await safe_edit_message(callback, "❌ Ошибка при загрузке лайков", reply_markup=kb.back_to_menu)

@router.callback_query(F.data == "my_dislikes")
@handle_network_errors
async def my_dislikes_handler(callback: CallbackQuery):
    """Показать дизлайкнутые квартиры"""
    user_id = callback.from_user.id
    
    try:
        disliked_apartments = await ReactionService.get_user_disliked_apartments(user_id, limit=10)
        
        if not disliked_apartments:
            await safe_edit_message(
                callback,
                "👎 **Скрытые квартиры**\n\n"
                "У вас пока нет скрытых квартир.\n"
                "Используйте кнопку 👎 при просмотре квартир, чтобы исключить их из результатов поиска.",
                parse_mode="Markdown",
                reply_markup=kb.back_to_menu
            )
            return
        
        response = "👎 **Скрытые квартиры:**\n\n"
        response += "_(Эти квартиры не показываются в результатах поиска)_\n\n"
        
        for i, apt in enumerate(disliked_apartments, 1):
            price_str = f"{apt.price:,} ₽" if apt.price else "цена не указана"
            price_per_sqm_str = f" ({apt.price_per_sqm:,} ₽/м²)" if apt.price_per_sqm else ""
            
            response += f"**{i}. {price_str}**{price_per_sqm_str}\n"
            response += f"_{apt.title[:80]}{'...' if len(apt.title) > 80 else ''}_\n"
            
            # Добавляем информацию о метро
            metro_info = [station.station_name for station in apt.metro_stations[:2]]
            metro_str = f"🚇 {', '.join(metro_info)}" if metro_info else ""
            if metro_str:
                response += f"{metro_str}\n"
            
            response += f"[Открыть на Cian]({apt.url})\n\n"
            
            if len(response) > 3500:  # Ограничиваем размер сообщения
                response += "...\n\n"
                break
        
        # Показываем статистику
        summary = await ReactionService.get_user_reactions_summary(user_id)
        response += f"📊 Всего дизлайков: {summary['dislikes']}"
        
        await safe_edit_message(
            callback,
            response,
            parse_mode="Markdown",
            reply_markup=kb.back_to_menu,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error in my_dislikes_handler: {e}")
        await safe_edit_message(callback, "❌ Ошибка при загрузке дизлайков", reply_markup=kb.back_to_menu)

@router.callback_query(F.data.startswith("remove_reaction_"))
@handle_network_errors
async def remove_reaction_handler(callback: CallbackQuery):
    """Удаление реакции из списка лайков/дизлайков"""
    user_id = callback.from_user.id
    
    try:
        apartment_id = int(callback.data.split('_')[2])
        
        # Удаляем реакцию
        removed = await ReactionService.remove_reaction(user_id, apartment_id)
        
        if removed:
            await callback.answer("✅ Реакция удалена", show_alert=True)
            # Можно обновить список, но пока просто уведомляем
        else:
            await callback.answer("❌ Реакция не найдена", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error in remove_reaction_handler: {e}")
        await callback.answer("❌ Ошибка при удалении реакции", show_alert=True)

# Команды для быстрого доступа к реакциям
@router.message(Command("liked"))
@handle_network_errors
async def liked_command_handler(message: Message):
    """Команда для просмотра лайкнутых квартир"""
    user_id = message.from_user.id
    
    try:
        liked_apartments = await ReactionService.get_user_liked_apartments(user_id, limit=5)
        
        if not liked_apartments:
            await message.answer(
                "❤️ **Ваши лайки**\n\n"
                "У вас пока нет лайкнутых квартир.\n"
                "Используйте /search для поиска квартир.",
                parse_mode="Markdown"
            )
            return
        
        response = "❤️ **Ваши любимые квартиры (топ-5):**\n\n"
        
        for i, apt in enumerate(liked_apartments, 1):
            price_str = f"{apt.price:,} ₽" if apt.price else "цена не указана"
            response += f"{i}. **{price_str}**\n"
            response += f"_{apt.title[:60]}{'...' if len(apt.title) > 60 else ''}_\n"
            response += f"[Открыть]({apt.url})\n\n"
        
        summary = await ReactionService.get_user_reactions_summary(user_id)
        response += f"📊 Всего лайков: {summary['likes']}"
        
        await message.answer(response, parse_mode="Markdown", disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error in liked_command_handler: {e}")
        await message.answer("❌ Ошибка при загрузке лайков")

@router.message(Command("disliked"))
@handle_network_errors
async def disliked_command_handler(message: Message):
    """Команда для просмотра дизлайкнутых квартир"""
    user_id = message.from_user.id
    
    try:
        disliked_apartments = await ReactionService.get_user_disliked_apartments(user_id, limit=5)
        
        if not disliked_apartments:
            await message.answer(
                "👎 **Скрытые квартиры**\n\n"
                "У вас пока нет скрытых квартир.",
                parse_mode="Markdown"
            )
            return
        
        response = "👎 **Скрытые квартиры (топ-5):**\n\n"
        response += "_(Эти квартиры не показываются в поиске)_\n\n"
        
        for i, apt in enumerate(disliked_apartments, 1):
            price_str = f"{apt.price:,} ₽" if apt.price else "цена не указана"
            response += f"{i}. **{price_str}**\n"
            response += f"_{apt.title[:60]}{'...' if len(apt.title) > 60 else ''}_\n"
            response += f"[Открыть]({apt.url})\n\n"
        
        summary = await ReactionService.get_user_reactions_summary(user_id)
        response += f"📊 Всего дизлайков: {summary['dislikes']}"
        
        await message.answer(response, parse_mode="Markdown", disable_web_page_preview=True)
        
    except Exception as e:
        logger.error(f"Error in disliked_command_handler: {e}")
        await message.answer("❌ Ошибка при загрузке дизлайков")
    