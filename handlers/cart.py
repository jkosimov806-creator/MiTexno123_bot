from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database
from utils import safe_edit_text


async def show_cart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    items = await database.get_cart(user_id)

    if not items:
        await safe_edit_text(
            query,
            "Ваша корзина пуста.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍 Перейти в каталог", callback_data="show_catalog")],
                [InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")],
            ]),
        )
        return

    total = sum(i["price"] * i["quantity"] for i in items)
    lines = [
        f"• {item['name']} x{item['quantity']} — {item['price'] * item['quantity']:.2f} сомонӣ"
        for item in items
    ]

    text = "🛒 *Ваша корзина:*\n\n" + "\n".join(lines) + f"\n\n💰 *Итого: {total:.2f} сомонӣ*"

    remove_buttons = [
        [InlineKeyboardButton(f"❌ Убрать {item['name']}", callback_data=f"remove_cart_{item['product_id']}")]
        for item in items
    ]
    remove_buttons.append([InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout")])
    remove_buttons.append([InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")])

    await safe_edit_text(
        query,
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(remove_buttons),
    )


async def remove_from_cart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Поправил срез индекса для получения ID продукта
    product_id = int(query.data.split("_")[2])
    user_id = query.from_user.id
    await database.remove_from_cart(user_id, product_id)

    await show_cart_handler(update, context)


async def show_orders_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    orders = await database.get_user_orders(user_id)

    if not orders:
        await safe_edit_text(
            query,
            "У вас пока нет заказов.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍 Перейти в каталог", callback_data="show_catalog")],
                [InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")],
            ]),
        )
        return

    import json
    lines = []
    for order in orders:
        items = json.loads(order["items_json"])
        items_str = ", ".join(f"{i['name']} x{i['quantity']}" for i in items)
        lines.append(
            f"📦 *Заказ #{order['id']}* — {order['created_at'][:10]}\n"
            f"   {items_str}\n"
            f"   Итого: {order['total']:.2f} сомонӣ | Статус: {order['status']}"
        )

    text = "📦 *Ваши заказы:*\n\n" + "\n\n".join(lines)
    await safe_edit_text(
        query,
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")]
        ]),
    )
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database
from utils import safe_edit_text


async def show_cart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    items = await database.get_cart(user_id)

    if not items:
        await safe_edit_text(
            query,
            "Ваша корзина пуста.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍 Перейти в каталог", callback_data="show_catalog")],
                [InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")],
            ]),
        )
        return

    total = sum(i["price"] * i["quantity"] for i in items)
    lines = [
        f"• {item['name']} x{item['quantity']} — {item['price'] * item['quantity']:.2f} сомонӣ"
        for item in items
    ]

    text = "🛒 *Ваша корзина:*\n\n" + "\n".join(lines) + f"\n\n💰 *Итого: {total:.2f} сомонӣ*"

    remove_buttons = [
        [InlineKeyboardButton(f"❌ Убрать {item['name']}", callback_data=f"remove_cart_{item['product_id']}")]
        for item in items
    ]
    remove_buttons.append([InlineKeyboardButton("✅ Оформить заказ", callback_data="checkout")])
    remove_buttons.append([InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")])

    await safe_edit_text(
        query,
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(remove_buttons),
    )


async def remove_from_cart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Поправил логику извлечения ID
    data_parts = query.data.split("_")
    product_id = int(data_parts[2]) if len(data_parts) > 2 else 0
    
    user_id = query.from_user.id
    await database.remove_from_cart(user_id, product_id)

    await show_cart_handler(update, context)


async def show_orders_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    orders = await database.get_user_orders(user_id)

    if not orders:
        await safe_edit_text(
            query,
            "У вас пока нет заказов.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍 Перейти в каталог", callback_data="show_catalog")],
                [InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")],
            ]),
        )
        return

    import json
    lines = []
    for order in orders:
        items = json.loads(order["items_json"])
        items_str = ", ".join(f"{i['name']} x{i['quantity']}" for i in items)
        lines.append(
            f"📦 *Заказ #{order['id']}* — {order['created_at'][:10]}\n"
            f"   {items_str}\n"
            f"   Итого: {order['total']:.2f} сомонӣ | Статус: {order['status']}"
        )

    text = "📦 *Ваши заказы:*\n\n" + "\n\n".join(lines)
    await safe_edit_text(
        query,
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")]
        ]),
    ) # <-- Вот эта скобка закрывает InlineKeyboardMarkup
) # <-- Вот эта скобка закрывает safe_edit_text
