from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="💳 Check Remaining Credit", callback_data="check_credit")],
        [InlineKeyboardButton(text="📜 My Recent Checks", callback_data="my_history")],
        [InlineKeyboardButton(text="ℹ️ Help & Instructions", callback_data="show_help")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_action")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_back_to_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="🔙 Back to Menu", callback_data="back_to_menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)
