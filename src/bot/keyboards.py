from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder

def get_main_keyboard(is_developer: bool = False) -> ReplyKeyboardMarkup:
    """Create main menu keyboard"""
    builder = ReplyKeyboardBuilder()
    
    # Standard buttons
    builder.add(KeyboardButton(text="🔍 Обзор объявлений"))
    builder.add(KeyboardButton(text="❤️ Избранное"))
    
    # Developer buttons
    if is_developer:
        builder.add(KeyboardButton(text="📊 Статистика"))
        builder.add(KeyboardButton(text="🔗 Управление URL"))
        builder.add(KeyboardButton(text="🚀 Запуск парсера"))
    
    # Adjust layout: 2 buttons per row
    builder.adjust(2)
    
    return builder.as_markup(resize_keyboard=True, placeholder="Выберите действие...")

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_offer_inline_keyboard(offer_id: int, offer_url: str, current_index: int, total_count: int, is_favorite: bool = False, sort_by: str = "score") -> InlineKeyboardMarkup:
    """Create inline keyboard for offer navigation and interaction"""
    builder = InlineKeyboardBuilder()
    
    # Interaction buttons
    like_text = "❤️ В избранном" if is_favorite else "🤍 В избранное"
    builder.row(
        InlineKeyboardButton(text="👎 Пропустить", callback_data=f"interact:dislike:{offer_id}:{current_index}:{sort_by}"),
        InlineKeyboardButton(text=like_text, callback_data=f"interact:like:{offer_id}:{current_index}:{sort_by}")
    )
    
    # Navigation buttons
    prev_index = (current_index - 1) % total_count
    next_index = (current_index + 1) % total_count
    
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data=f"browse:{prev_index}:{sort_by}"),
        InlineKeyboardButton(text=f"{current_index + 1}/{total_count}", callback_data="ignore"),
        InlineKeyboardButton(text="Вперед ➡️", callback_data=f"browse:{next_index}:{sort_by}")
    )

    # Sort toggle
    sort_text = "📊 Сорт: Баллы" if sort_by == "score" else "👁️ Сорт: Просмотры"
    new_sort = "views" if sort_by == "score" else "score"
    builder.row(
        InlineKeyboardButton(text=sort_text, callback_data=f"sort:{new_sort}:{current_index}")
    )
    
    return builder.as_markup()
