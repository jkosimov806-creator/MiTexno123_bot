from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import types

def main_kb(user_id, admin_id):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="▻ КАТАЛОГ", callback_data="catalog_0"))
    kb.row(types.InlineKeyboardButton(text="🛒 КОРЗИНА", callback_data="view_cart"))
    kb.row(types.InlineKeyboardButton(text="🛡 ПОДДЕРЖКА", callback_data="support_info"))
    if user_id == admin_id:
        kb.row(types.InlineKeyboardButton(text="⚙️ АДМИНКА", callback_data="admin_menu"))
    return kb.as_markup()
