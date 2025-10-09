from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

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