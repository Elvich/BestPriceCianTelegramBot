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
            InlineKeyboardButton(text="❤️ Мои лайки", callback_data="my_likes"),
            InlineKeyboardButton(text="👎 Дизлайки", callback_data="my_dislikes")
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

# Функции для создания кнопок реакций
def create_apartment_reaction_keyboard(apartment_id: int, current_reaction: str = None) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с кнопками лайка/дизлайка для квартиры
    
    Args:
        apartment_id: ID квартиры
        current_reaction: Текущая реакция пользователя ('like'/'dislike'/None)
    """
    # Определяем эмодзи в зависимости от текущей реакции
    like_emoji = "❤️" if current_reaction == "like" else "🤍"
    dislike_emoji = "👎" if current_reaction == "dislike" else "👌"
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{like_emoji} Нравится",
                    callback_data=f"reaction_like_{apartment_id}"
                ),
                InlineKeyboardButton(
                    text=f"{dislike_emoji} Не нравится",
                    callback_data=f"reaction_dislike_{apartment_id}"
                )
            ]
        ]
    )

def create_apartment_detail_keyboard(apartment_id: int, current_reaction: str = None) -> InlineKeyboardMarkup:
    """
    Создает расширенную клавиатуру для детального просмотра квартиры
    
    Args:
        apartment_id: ID квартиры
        current_reaction: Текущая реакция пользователя ('like'/'dislike'/None)
    """
    # Определяем эмодзи в зависимости от текущей реакции
    like_emoji = "❤️" if current_reaction == "like" else "🤍"
    dislike_emoji = "👎" if current_reaction == "dislike" else "👌"
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"{like_emoji} Нравится",
                    callback_data=f"reaction_like_{apartment_id}"
                ),
                InlineKeyboardButton(
                    text=f"{dislike_emoji} Не нравится",
                    callback_data=f"reaction_dislike_{apartment_id}"
                )
            ],
            [
                InlineKeyboardButton(text="🔗 Открыть на Cian", url=f"https://cian.ru/rent/flat/{apartment_id}/"),
            ],
            [
                InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")
            ]
        ]
    )

# Меню лайков и дизлайков
reactions_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="❤️ Мои лайки", callback_data="my_likes"),
            InlineKeyboardButton(text="👎 Мои дизлайки", callback_data="my_dislikes")
        ],
        [
            InlineKeyboardButton(text="📊 Статистика реакций", callback_data="reactions_stats")
        ],
        [
            InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")
        ]
    ]
)

# Кнопки для управления реакциями в списке лайков/дизлайков
def create_reaction_management_keyboard(apartment_id: int, reaction_type: str) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру для управления реакциями в списке лайков/дизлайков
    
    Args:
        apartment_id: ID квартиры
        reaction_type: 'like' или 'dislike'
    """
    remove_text = "💔 Убрать лайк" if reaction_type == "like" else "✅ Убрать дизлайк"
    
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=remove_text,
                    callback_data=f"remove_reaction_{apartment_id}"
                )
            ],
            [
                InlineKeyboardButton(text="🔗 Открыть на Cian", url=f"https://cian.ru/rent/flat/{apartment_id}/"),
            ]
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