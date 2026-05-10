from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

import database
from utils import safe_edit_text


async def show_catalog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    categories = await database.get_categories()
    if not categories:
        await safe_edit_text(
            query,
            "Категорий пока нет. Попросите администратора добавить их!",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
            ]),
        )
        return

    buttons = [
        [InlineKeyboardButton(cat["name"], callback_data=f"cat_{cat['id']}")]
        for cat in categories
    ]
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")])

    await safe_edit_text(
        query,
        "Выберите категорию:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    category_id = int(query.data.split("_")[1])
    category = await database.get_category(category_id)
    products = await database.get_products_by_category(category_id)

    if not products:
        await safe_edit_text(
            query,
            f"В категории *{category['name']}* пока нет товаров.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К категориям", callback_data="show_catalog")]
            ]),
        )
        return

    buttons = [
        [InlineKeyboardButton(f"{p['name']} — {p['price']:.2f} сомонӣ", callback_data=f"prod_{p['id']}")]
        for p in products
    ]
    buttons.append([InlineKeyboardButton("⬅️ К категориям", callback_data="show_catalog")])

    await safe_edit_text(
        query,
        f"*{category['name']}* — выберите товар:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def show_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[1])
    product = await database.get_product(product_id)
    if not product:
        await safe_edit_text(query, "Товар не найден.")
        return

    caption = (
        f"*{product['name']}*\n"
        f"{product['description'] or ''}\n\n"
        f"💰 Цена: *{product['price']:.2f} сомонӣ*"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Добавить в корзину", callback_data=f"add_cart_{product['id']}")],
        [InlineKeyboardButton("⬅️ Назад", callback_data=f"cat_{product['category_id']}")],
    ])

    if product.get("photo_file_id"):
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_photo(
            photo=product["photo_file_id"],
            caption=caption,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )
    else:
        await safe_edit_text(
            query,
            caption,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )


async def add_to_cart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    product_id = int(query.data.split("_")[2])
    user_id = query.from_user.id
    await database.add_to_cart(user_id, product_id)
    product = await database.get_product(product_id)

    await query.answer(f"✅ {product['name']} добавлен в корзину!", show_alert=False)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 Перейти в корзину", callback_data="show_cart")],
        [InlineKeyboardButton("⬅️ К категории", callback_data=f"cat_{product['category_id']}")],
    ])

    try:
        await query.edit_message_reply_markup(reply_markup=keyboard)
    except Exception:
        try:
            await query.edit_message_caption(
                caption=query.message.caption,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
        except Exception:
            pass


def get_catalog_handlers():
    return [
        CallbackQueryHandler(show_catalog, pattern="^show_catalog$"),
        CallbackQueryHandler(show_category, pattern="^cat_\\d+$"),
        CallbackQueryHandler(show_product, pattern="^prod_\\d+$"),
        CallbackQueryHandler(add_to_cart_handler, pattern="^add_cart_\\d+$"),
    ]
