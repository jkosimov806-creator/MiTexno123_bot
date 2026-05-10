from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
import database
from utils import safe_edit_text


async def show_catalog_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    categories = await database.get_categories()

    if not categories:
        await safe_edit_text(query, "📦 Категории пока не добавлены.")
        return

    keyboard = []

    for cat in categories:
        cat = str(cat)
        keyboard.append([
            InlineKeyboardButton(cat, callback_data=f"cat_{cat}_0")
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
    category_name = data[1]
    current_index = int(data[2])

    products = await database.get_products_by_category(category_name)

    if not products:
        await safe_edit_text(
            query,
            "В этой категории пока нет товаров.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="show_catalog")]
            ])
        )
        return

    if current_index >= len(products):
        current_index = 0

    product = products[current_index]
    total = len(products)

    text = (
        f"🏷 *{product['name']}*\n\n"
        f"📝 {product['description']}\n\n"
        f"💰 Цена: *{product['price']:.2f} сомонӣ*\n"
        f"📦 В наличии: {product['stock']} шт.\n"
    )

    keyboard = []

    if total > 1:
        prev_idx = current_index - 1 if current_index > 0 else total - 1
        next_idx = current_index + 1 if current_index < total - 1 else 0

        keyboard.append([
            InlineKeyboardButton("⬅️", callback_data=f"cat_{category_name}_{prev_idx}"),
            InlineKeyboardButton(f"{current_index+1}/{total}", callback_data="ignore"),
            InlineKeyboardButton("➡️", callback_data=f"cat_{category_name}_{next_idx}")
        ])

    keyboard.append([
        InlineKeyboardButton("🛒 Купить", callback_data=f"buy_{product['id']}")
    ])

    keyboard.append([
        InlineKeyboardButton("📂 Категории", callback_data="show_catalog")
    ])

    await safe_edit_text(
        query,
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def add_to_cart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[1])
    user_id = query.from_user.id

    await database.add_to_cart(user_id, product_id, 1)

    await query.answer("Добавлено в корзину", show_alert=False)


def get_catalog_handlers():
    return [
        CallbackQueryHandler(show_catalog_handler, pattern="^show_catalog$"),
        CallbackQueryHandler(show_category_products, pattern="^cat_"),
        CallbackQueryHandler(add_to_cart_handler, pattern="^buy_"),
    ]
