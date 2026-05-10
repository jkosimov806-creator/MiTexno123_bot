from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database
from utils import safe_edit_text
import urllib.parse


async def show_catalog_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    categories = await database.get_categories()

    if not categories:
        await safe_edit_text(query, "📦 Категории пока не добавлены.")
        return

    keyboard = []

    for cat in categories:
        cat_str = str(cat)

        # защита от крашей Telegram
        safe_cat = urllib.parse.quote(cat_str)

        keyboard.append([
            InlineKeyboardButton(cat_str, callback_data=f"cat_{safe_cat}_0")
        ])

    keyboard.append([
        InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")
    ])

    await safe_edit_text(
        query,
        "📂 *Выберите категорию товаров:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def show_category_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split("_")

    category_name = urllib.parse.unquote(data[1])
    current_index = int(data[2])

    products = await database.get_products_by_category(category_name)

    if not products:
        await safe_edit_text(
            query,
            "В этой категории пока нет товаров.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback
