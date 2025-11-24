from aiogram import Router, F 
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramNetworkError, TelegramBadRequest
import Bot.keyboard as kb
import sys
import os
import logging
from functools import wraps
from Bot.error_handlers import network_retry, RetryConfig, NetworkMonitor

# Добавляем путь к родительской директории
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from DB.apartment_service import ApartmentService
from DB.notification_service import NotificationService
from DB.user_service import UserService
from DB.reaction_service import ReactionService
from scripts.excel_exporter import ExcelExporter
from Bot.notification_sender import NotificationSender

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()

# Конфигурация для повторных попыток (используем значения по умолчанию из config)
RETRY_CONFIG = RetryConfig()

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
    new_indicator = f"\n\n🆕 Я нашел {new_count} новых квартир!" if new_count > 0 else ""
    
    await message.answer(
        text=f"""Привет, {message.from_user.full_name}! 🏠

Я бот для поиска квартир на Циан по выгодным ценам.

Как только появятся новые выгодные квартиры, я отправлю уведомление.

или

Используй кнопки ниже для навигации{new_indicator}""", 
        reply_markup=kb.main_menu
    )

@router.message(Command("search"))
@handle_network_errors
async def search_apartments_handler(message: Message, state: FSMContext):
    """Обработчик команды поиска квартир - перенаправляет на плеер"""
    await message.answer(
        "🏠 **Теперь доступен удобный плеер для просмотра квартир!**\n\n"
        "Используйте кнопку ниже для перехода к новому интерфейсу.",
        parse_mode="Markdown",
        reply_markup=kb.main_menu
    )

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

@router.callback_query(F.data == "help")
@handle_network_errors
async def help_callback_handler(callback: CallbackQuery):
    """Обработчик кнопки помощи"""
    help_text = """ℹ️ **Справка по боту**

**Доступные функции:**
🏠 /start - Основное меню
📊 /stats - Статистика базы данных  
🆕 /recent - Недавно добавленные объявления
❤️ /liked - Избранные квартиры
👎 /disliked - Скрытые квартиры
📄 /export - Экспорт данных в Excel формат

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
• Экспорт данных в Excel с красивым оформлением"""

    await safe_edit_message(callback, help_text, parse_mode="Markdown", reply_markup=kb.back_to_menu)

@router.callback_query(F.data == "back_to_menu")
@handle_network_errors
async def back_to_menu_handler(callback: CallbackQuery):
    """Возврат в главное меню"""
    text = f"""Привет, {callback.from_user.full_name}! 🏠

Я бот для поиска квартир на Циан по выгодным ценам.
"""
    
    await safe_edit_message(callback, text, reply_markup=kb.main_menu)

@router.callback_query(F.data.startswith("back_to_list_"))
@handle_network_errors
async def back_to_list_handler(callback: CallbackQuery):
    """Возврат к списку (из плеера обратно к обзору списка)"""
    try:
        list_context = callback.data.split('_')[3]
        
        if list_context == "liked":
            await my_likes_handler(callback)
        elif list_context == "disliked":
            await my_dislikes_handler(callback)
        elif list_context == "new":
            await recent_callback_handler(callback)
        elif list_context.startswith("views_"):
            await browse_apartments_list_helper(callback, index=0, list_context=list_context)
            
    except Exception as e:
        logger.error(f"Error in back_to_list_handler: {e}")
        await safe_edit_message(callback, "❌ Ошибка при возврате к списку", reply_markup=kb.back_to_menu)

@router.callback_query(F.data == "browse_all")
@handle_network_errors
async def browse_all_handler(callback: CallbackQuery):
    """Просмотр всех квартир"""
    await browse_apartments_helper(callback, index=0)
    await callback.answer()

@router.callback_query(F.data == "back_to_browse_menu")
@handle_network_errors
async def back_to_browse_menu_handler(callback: CallbackQuery):
    """Возврат в меню просмотра"""
    await safe_edit_message(
        callback, 
        "🔍 **Выберите режим просмотра:**", 
        reply_markup=kb.browse_menu,
        parse_mode="Markdown"
    )

@router.callback_query(F.data.in_({"browse_views_100", "browse_views_200"}))
@handle_network_errors
async def browse_views_handler(callback: CallbackQuery):
    """Просмотр популярных квартир"""
    min_views = 100 if "100" in callback.data else 200
    context = f"views_{min_views}"
    await browse_apartments_list_helper(callback, index=0, list_context=context)
    await callback.answer()

# Обработчики кнопок главного меню
@router.callback_query(F.data == "browse")
@handle_network_errors
async def browse_apartments_handler(callback: CallbackQuery):
    """Меню просмотра квартир"""
    await safe_edit_message(
        callback, 
        "🔍 **Выберите режим просмотра:**", 
        reply_markup=kb.browse_menu,
        parse_mode="Markdown"
    )

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
        await browse_apartments_list_helper(callback, index=0, list_context="new")
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in recent_callback_handler: {e}")
        await safe_edit_message(callback, f"❌ Ошибка при получении новых квартир: {str(e)}", reply_markup=kb.back_to_menu)



async def browse_apartments_helper(callback: CallbackQuery, index: int = 0):
    """Помощник для просмотра квартир в режиме плеера"""
    try:
        user_id = callback.from_user.id
        
        # Получаем все квартиры, исключая дизлайкнутые пользователем
        apartments = await ApartmentService.get_apartments(
            limit=50,  # Берем больше квартир для просмотра
            only_active=True,
            only_production=True,
            exclude_disliked_for_user=user_id
        )
        
        if not apartments:
            await safe_edit_message(
                callback, 
                "❌ Квартиры не найдены. Возможно, база данных пуста.",
                reply_markup=kb.back_to_menu
            )
            return
        
        # Проверяем, что индекс в пределах списка
        if index < 0 or index >= len(apartments):
            index = 0
        
        apartment = apartments[index]
        
        # Получаем текущую реакцию пользователя
        current_reaction = await ReactionService.get_user_reaction(user_id, apartment.id)
        
        # Формируем информацию о квартире
        price_str = f"{apartment.price:,} ₽" if apartment.price else "цена не указана"
        price_per_sqm_str = f" ({apartment.price_per_sqm:,} ₽/м²)" if apartment.price_per_sqm else ""
        
        metro_info = []
        for metro in apartment.metro_stations[:2]:
            metro_info.append(f"{metro.station_name} {metro.travel_time}")
        metro_str = f"\n🚇 {', '.join(metro_info)}" if metro_info else ""
        
        address_str = f"\n📍 {apartment.address}" if apartment.address else ""
        
        apartment_info = f"**{price_str}**{price_per_sqm_str}"
        apartment_info += f"\n{apartment.title}"
        apartment_info += metro_str
        apartment_info += address_str
        apartment_info += f"\n\n🔗 [Открыть на Cian]({apartment.url})"
        
        # Информация о позиции в списке
        position_info = f"📋 **Квартира {index + 1} из {len(apartments)}**\n\n"
        
        text = position_info + apartment_info
        
        # Создаем клавиатуру плеера
        keyboard = kb.create_apartment_browser_keyboard(
            current_index=index,
            total_count=len(apartments),
            apartment_id=apartment.id,
            current_reaction=current_reaction,
            list_context="all"
        )
        
        await safe_edit_message(
            callback,
            text,
            parse_mode="Markdown",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error in browse_apartments_helper: {e}")
        await safe_edit_message(
            callback,
            f"❌ Ошибка при загрузке квартир: {str(e)}",
            reply_markup=kb.back_to_menu
        )

async def browse_apartments_list_helper(callback: CallbackQuery, index: int, list_context: str):
    """Универсальная функция для просмотра списков квартир в режиме плеера"""
    try:
        user_id = callback.from_user.id
        
        # Получаем квартиры в зависимости от контекста
        if list_context == "all":
            apartments = await ApartmentService.get_apartments(
                limit=50,
                only_active=True,
                only_production=True,
                exclude_disliked_for_user=user_id
            )
            title_prefix = "🏠 Просмотр квартир"
        elif list_context == "liked":
            apartments = await ReactionService.get_user_liked_apartments(user_id, limit=50)
            title_prefix = "❤️ Ваши лайки"
        elif list_context == "disliked":
            apartments = await ReactionService.get_user_disliked_apartments(user_id, limit=50)
            title_prefix = "👎 Скрытые квартиры"
        elif list_context == "new":
            apartments = await NotificationService.get_new_apartments_for_user(user_id, limit=50)
            title_prefix = "🆕 Новые квартиры"
        elif list_context == "views_100":
            apartments = await ApartmentService.get_apartments(
                limit=50,
                only_active=True,
                only_production=True,
                exclude_disliked_for_user=user_id,
                min_views=100
            )
            title_prefix = ">100 просмотров"
        elif list_context == "views_200":
            apartments = await ApartmentService.get_apartments(
                limit=50,
                only_active=True,
                only_production=True,
                exclude_disliked_for_user=user_id,
                min_views=200
            )
            title_prefix = ">200 просмотров"
        else:
            apartments = []
            title_prefix = "📋 Квартиры"
        
        if not apartments:
            empty_messages = {
                "all": "❌ Квартиры не найдены. Возможно, база данных пуста.",
                "liked": "❤️ У вас пока нет лайкнутых квартир.\nИспользуйте кнопку ❤️ при просмотре квартир.",
                "disliked": "👎 У вас пока нет скрытых квартир.\nИспользуйте кнопку 👎 при просмотре квартир.",
                "new": "🆕 Новых квартир для вас пока нет.",
                "views_100": "Квартир с >100 просмотров пока нет.",
                "views_200": "Квартир с >200 просмотров пока нет."
            }
            
            await safe_edit_message(
                callback, 
                empty_messages.get(list_context, "❌ Квартиры не найдены."),
                reply_markup=kb.back_to_menu
            )
            return
        
        # Проверяем, что индекс в пределах списка
        if index < 0 or index >= len(apartments):
            index = 0
        
        apartment = apartments[index]
        
        # Получаем текущую реакцию пользователя
        current_reaction = await ReactionService.get_user_reaction(user_id, apartment.id)
        
        # Формируем информацию о квартире
        price_str = f"{apartment.price:,} ₽" if apartment.price else "цена не указана"
        price_per_sqm_str = f" ({apartment.price_per_sqm:,} ₽/м²)" if apartment.price_per_sqm else ""
        
        metro_info = []
        for metro in apartment.metro_stations[:2]:
            metro_info.append(f"{metro.station_name} {metro.travel_time}")
        metro_str = f"\n🚇 {', '.join(metro_info)}" if metro_info else ""
        
        address_str = f"\n📍 {apartment.address}" if apartment.address else ""
        
        apartment_info = f"**{price_str}**{price_per_sqm_str}"
        apartment_info += f"\n{apartment.title}"
        apartment_info += metro_str
        apartment_info += address_str
        apartment_info += f"\n\n🔗 [Открыть на Cian]({apartment.url})"
        
        # Информация о позиции в списке
        position_info = f"📋 **{title_prefix} - {index + 1} из {len(apartments)}**\n\n"
        
        text = position_info + apartment_info
        
        # Создаем клавиатуру плеера
        keyboard = kb.create_apartment_browser_keyboard(
            current_index=index,
            total_count=len(apartments),
            apartment_id=apartment.id,
            current_reaction=current_reaction,
            list_context=list_context
        )
        
        await safe_edit_message(
            callback,
            text,
            parse_mode="Markdown",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error in browse_apartments_list_helper: {e}")
        await safe_edit_message(
            callback,
            f"❌ Ошибка при загрузке квартир: {str(e)}",
            reply_markup=kb.back_to_menu
        )

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

@router.callback_query(F.data == "export_browse")
@handle_network_errors
async def export_browse_handler(callback: CallbackQuery):
    """Экспорт квартир для просмотра пользователя"""
    await callback.answer("⏳ Создаем Excel файл...", show_alert=True)
    
    try:
        user_id = callback.from_user.id
        
        await safe_edit_message(callback, "⏳ **Создание Excel файла с квартирами для просмотра...**\n\nПожалуйста, подождите.", parse_mode="Markdown")
        
        file_path = await ExcelExporter.export_browse_apartments_to_excel(user_id)
        
        from aiogram.types import FSInputFile
        document = FSInputFile(file_path)
        
        await callback.message.answer_document(
            document=document,
            caption="🏠 **Квартиры для просмотра**\n\nВ файле содержатся все доступные вам квартиры (исключены ваши дизлайки).",
            parse_mode="Markdown"
        )
        
        os.remove(file_path)
        await safe_edit_message(callback, "✅ **Файл с квартирами для просмотра отправлен!**\n\nВыберите другой тип экспорта:", parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in export_browse_handler: {e}")
        await safe_edit_message(callback, f"❌ **Ошибка при создании файла:**\n{str(e)}", parse_mode="Markdown", reply_markup=kb.export_menu)

@router.callback_query(F.data == "export_liked")
@handle_network_errors
async def export_liked_handler(callback: CallbackQuery):
    """Экспорт лайкнутых пользователем квартир"""
    await callback.answer("⏳ Создаем Excel файл...", show_alert=True)
    
    try:
        user_id = callback.from_user.id
        
        await safe_edit_message(callback, "⏳ **Создание Excel файла с вашими лайками...**\n\nПожалуйста, подождите.", parse_mode="Markdown")
        
        file_path = await ExcelExporter.export_user_liked_apartments_to_excel(user_id)
        
        from aiogram.types import FSInputFile
        document = FSInputFile(file_path)
        
        await callback.message.answer_document(
            document=document,
            caption="❤️ **Ваши лайкнутые квартиры**\n\nВ файле содержатся все квартиры, которые вы добавили в избранное.",
            parse_mode="Markdown"
        )
        
        os.remove(file_path)
        await safe_edit_message(callback, "✅ **Файл с вашими лайками отправлен!**\n\nВыберите другой тип экспорта:", parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Error in export_liked_handler: {e}")
        await safe_edit_message(callback, f"❌ **Ошибка при создании файла:**\n{str(e)}", parse_mode="Markdown", reply_markup=kb.export_menu)

@router.callback_query(F.data == "export_all")
@handle_network_errors
async def export_all_handler(callback: CallbackQuery):
    """Экспорт всех объявлений"""
    await callback.answer("⏳ Создаем Excel файл...", show_alert=True)
    
    try:
        # Показываем сообщение о процессе
        await safe_edit_message(callback, "⏳ **Создание Excel файла...**\n\nПожалуйста, подождите. Это может занять некоторое время.", parse_mode="Markdown")
        
        # Создаем Excel файл
        file_path = await ExcelExporter.export_apartments_to_excel()  # Экспортируем все данные
        
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


        
    except Exception as e:
        logger.error(f"Error in export_top50_handler: {e}")
        await safe_edit_message(callback, f"❌ **Ошибка при создании топ-50:**\n{str(e)}", parse_mode="Markdown", reply_markup=kb.export_menu)

# ===== ОБРАБОТЧИКИ НАВИГАЦИИ В ПЛЕЕРЕ =====

@router.callback_query(F.data.startswith("browse_prev_"))
@handle_network_errors
async def browse_previous_handler(callback: CallbackQuery):
    """Переход к предыдущей квартире в плеере"""
    try:
        # Извлекаем данные из callback_data
        parts = callback.data.split('_')
        current_index = int(parts[2])
        list_context = parts[3] if len(parts) > 3 else "all"
        new_index = current_index - 1
        
        if new_index >= 0:
            if list_context == "all":
                await browse_apartments_helper(callback, index=new_index)
            else:
                await browse_apartments_list_helper(callback, index=new_index, list_context=list_context)
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in browse_previous_handler: {e}")
        await callback.answer("❌ Ошибка при переходе")

@router.callback_query(F.data.startswith("browse_next_"))
@handle_network_errors
async def browse_next_handler(callback: CallbackQuery):
    """Переход к следующей квартире в плеере"""
    try:
        # Извлекаем данные из callback_data
        parts = callback.data.split('_')
        current_index = int(parts[2])
        list_context = parts[3] if len(parts) > 3 else "all"
        new_index = current_index + 1
        
        # Функции сами проверят границы
        if list_context == "all":
            await browse_apartments_helper(callback, index=new_index)
        else:
            await browse_apartments_list_helper(callback, index=new_index, list_context=list_context)
        
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Error in browse_next_handler: {e}")
        await callback.answer("❌ Ошибка при переходе")

# ===== ОБРАБОТЧИКИ РЕАКЦИЙ =====

@router.callback_query(F.data.startswith("reaction_"))
@handle_network_errors
async def reaction_handler(callback: CallbackQuery):
    """Обработчик кнопок лайка/дизлайка"""
    user_id = callback.from_user.id
    
    # Парсим callback_data: "reaction_like_123_context_index" или "reaction_dislike_123"
    try:
        parts = callback.data.split('_')
        reaction_type = parts[1]  # 'like' или 'dislike'
        apartment_id = int(parts[2])
        list_context = parts[3] if len(parts) > 3 else "all"
        current_index = int(parts[4]) if len(parts) > 4 else 0
    except (IndexError, ValueError):
        await callback.answer("❌ Ошибка в данных", show_alert=True)
        return
    
    try:
        # Получаем текущую реакцию пользователя
        current_reaction = await ReactionService.get_user_reaction(user_id, apartment_id)
        
        # Логика противоположных реакций
        if current_reaction and current_reaction != reaction_type:
            # Если есть противоположная реакция, убираем её и ставим новую
            await ReactionService.remove_reaction(user_id, apartment_id)
            result = await ReactionService.toggle_reaction(user_id, apartment_id, reaction_type)
            
            if reaction_type == 'like':
                message = "❤️ Убрали дизлайк и поставили лайк!"
            else:
                message = "👎 Убрали лайк и поставили дизлайк!"
        else:
            # Обычное переключение реакции
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
            else:
                message = "✅ Реакция обновлена"
        
        await callback.answer(message, show_alert=True)
        
        # Обновляем плеер с актуальными данными
        if list_context == "all":
            await browse_apartments_helper(callback, index=current_index)
        else:
            await browse_apartments_list_helper(callback, index=current_index, list_context=list_context)
            
    except Exception as e:
        logger.error(f"Error in reaction_handler: {e}")
        await callback.answer("❌ Ошибка при обработке реакции", show_alert=True)

@router.callback_query(F.data == "my_likes")
@handle_network_errors  
async def my_likes_handler(callback: CallbackQuery):
    """Показать лайкнутые квартиры в плеере"""
    await browse_apartments_list_helper(callback, index=0, list_context="liked")
    await callback.answer()

@router.callback_query(F.data == "my_dislikes")
@handle_network_errors
async def my_dislikes_handler(callback: CallbackQuery):
    """Показать дизлайкнутые квартиры в плеере"""
    await browse_apartments_list_helper(callback, index=0, list_context="disliked")
    await callback.answer()

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
    await message.answer(
        "❤️ **Ваши лайки**\n\nИспользуйте кнопку ниже для просмотра в плеере:",
        parse_mode="Markdown",
        reply_markup=kb.main_menu
    )

@router.message(Command("disliked"))
@handle_network_errors
async def disliked_command_handler(message: Message):
    """Команда для просмотра дизлайкнутых квартир"""
    await message.answer(
        "👎 **Скрытые квартиры**\n\nИспользуйте кнопку ниже для просмотра в плеере:",
        parse_mode="Markdown",
        reply_markup=kb.main_menu
    )
    