from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

# Главное меню
main_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🏠 Просмотр квартир", callback_data="browse"),
        ],
        [
            InlineKeyboardButton(text="❤️ Мои лайки", callback_data="my_likes"),
            InlineKeyboardButton(text="🆕 Новые объявления", callback_data="recent")
        ],
        [
    
            InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")
        ]
    ]
)

# Меню экспорта
export_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="🏠 Все", callback_data="export_browse"),
            InlineKeyboardButton(text="❤️ Мои лайки", callback_data="export_liked")
        ],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_to_menu")]
    ]
)

# Меню выбора режима просмотра
browse_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Все квартиры", callback_data="browse_all")],
        [InlineKeyboardButton(text=">= 100 просмотров", callback_data="browse_views_100"),
        InlineKeyboardButton(text=">= 200 просмотров", callback_data="browse_views_200")
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
    dislike_emoji = "👎" 
    
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
    dislike_emoji = "👎" 
    
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

def create_apartment_browser_keyboard(current_index: int, total_count: int, apartment_id: int, 
                                    current_reaction: str = None, list_context: str = "all") -> InlineKeyboardMarkup:
    """
    Создает клавиатуру плеера для просмотра квартир с навигацией
    
    Args:
        current_index: Текущий индекс квартиры (начиная с 0)
        total_count: Общее количество квартир
        apartment_id: ID текущей квартиры
        current_reaction: Текущая реакция пользователя ('like'/'dislike'/None)
        list_context: Контекст списка ('all'/'liked'/'disliked'/'new')
    """
    # Определяем эмодзи в зависимости от текущей реакции
    like_emoji = "❤️" if current_reaction == "like" else "🤍"
    dislike_emoji = "👎"
    
    keyboard = []
    
    # Первая строчка: Навигация и реакции
    first_row = []
    
    # Кнопка "Назад" (если не первая квартира)
    if current_index > 0:
        first_row.append(InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"browse_prev_{current_index}_{list_context}"
        ))
    
    # Кнопки реакций
    first_row.append(InlineKeyboardButton(
        text=f"{like_emoji}",
        callback_data=f"reaction_like_{apartment_id}_{list_context}_{current_index}"
    ))
    first_row.append(InlineKeyboardButton(
        text=f"{dislike_emoji}",
        callback_data=f"reaction_dislike_{apartment_id}_{list_context}_{current_index}"
    ))
    
    # Кнопка "Вперед" (если не последняя квартира)
    if current_index < total_count - 1:
        first_row.append(InlineKeyboardButton(
            text="➡️ Вперед",
            callback_data=f"browse_next_{current_index}_{list_context}"
        ))
    
    keyboard.append(first_row)
    
    # Вторая строчка: Возврат к списку и главное меню
    second_row = []
    
    # Кнопка возврата (зависит от контекста)
    if list_context in ["all"] or list_context.startswith("views_"):
        # Если пришли из меню просмотра, возвращаемся в него
        second_row.append(InlineKeyboardButton(
            text="🔙 Вернуться", 
            callback_data="back_to_browse_menu"
        ))
    else:
        # Иначе возвращаемся в главное меню
        second_row.append(InlineKeyboardButton(
            text="🏠 Главное меню", 
            callback_data="back_to_menu"
        ))
    
    keyboard.append(second_row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

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