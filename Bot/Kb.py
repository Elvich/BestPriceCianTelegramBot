from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# Главное меню
main_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🔍 Поиск квартир", callback_data="search"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats")
        ],
        [
            InlineKeyboardButton(text="🚇 Станции метро", callback_data="metro"),
            InlineKeyboardButton(text="🆕 Новые объявления", callback_data="recent")
        ],
        [
            InlineKeyboardButton(text="📄 Экспорт в Excel", callback_data="export_menu"),
            InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")
        ]
    ]
)

# Меню экспорта
export_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Все объявления", callback_data="export_all"),
            InlineKeyboardButton(text="💰 До 20 млн", callback_data="export_cheap")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика", callback_data="export_stats"),
            InlineKeyboardButton(text="🎯 Топ-50 дешевых", callback_data="export_top50")
        ],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
    ]
)

# Кнопка возврата в меню  
back_to_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
    ]
)

# Старые клавиатуры для совместимости
section = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Помощь", callback_data="help"),
        InlineKeyboardButton(text="Ответ", callback_data="answer")]
    ]
)

exit = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="Выйти в главное меню", callback_data="exit")]
    ]
)