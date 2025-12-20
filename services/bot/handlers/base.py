from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
import services.bot.keyboards as kb
from core.database.notification_service import NotificationService
from services.bot.handlers.common import handle_network_errors, safe_edit_message

router = Router()

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
