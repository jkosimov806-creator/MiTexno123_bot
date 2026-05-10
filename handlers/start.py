from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from utils import safe_edit_text

MAIN_MENU_TEXT = "Добро пожаловать в магазин! Что вы хотите сделать?"


def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍 Каталог товаров", callback_data="show_catalog")],
        [InlineKeyboardButton("🛒 Моя корзина", callback_data="show_cart")],
        [InlineKeyboardButton("📦 Мои заказы", callback_data="show_orders")],
        [InlineKeyboardButton("👛 Кошелёк", callback_data="show_wallet")],
    ])


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MAIN_MENU_TEXT, reply_markup=main_menu_keyboard())


async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await safe_edit_text(query, MAIN_MENU_TEXT, reply_markup=main_menu_keyboard())
