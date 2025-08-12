
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


main = ReplyKeyboardMarkup(keyboard=[
    [KeyboardButton(text="Current weather 🌤️"),
    KeyboardButton(text="Weather history (1 month)")],

    ], resize_keyboard=True, one_time_keyboard=True)

return_to_main = ReplyKeyboardMarkup(
    keyboard=[
            [KeyboardButton(text="⏪ Main menu")]
        ],
        resize_keyboard=True
    )