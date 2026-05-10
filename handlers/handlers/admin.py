import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    CommandHandler,
    filters,
)

import database
from config import is_admin

(
    ADMIN_MENU,
    ADD_CAT_NAME,
    ADD_PROD_SELECT_CAT,
    ADD_PROD_NAME,
    ADD_PROD_DESC,
    ADD_PROD_PRICE,
    ADD_PROD_PHOTO,
    ORDER_DETAIL,
    DEL_PROD_SELECT_CAT,
    DEL_PROD_LIST,
    DEL_CAT_LIST,
    ADD_PROMO_CODE,
    ADD_PROMO_BALANCE,
    PROMO_LIST,
) = range(14)

STATUSES = {
    "new":        "🆕 Новый",
    "processing": "⚙️ В обработке",
    "shipped":    "🚚 Отправлен",
    "delivered":  "✅ Доставлен",
    "confirmed":  "✅ Оплачен",
    "cancelled":  "❌ Отменён",
}

STATUS_NOTIFY = {
    "processing": "⚙️ Ваш заказ *#{id}* принят в обработку.",
    "shipped":    "🚚 Ваш заказ *#{id}* отправлен! Ожидайте доставки.",
    "delivered":  "✅ Ваш заказ *#{id}* доставлен. Спасибо за покупку!",
    "cancelled":  "❌ Ваш заказ *#{id}* был отменён. Свяжитесь с нами для уточнения.",
}


def admin_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📁 Добавить категорию", callback_data="admin_add_cat")],
        [InlineKeyboardButton("📦 Добавить товар", callback_data="admin_add_prod")],
        [InlineKeyboardButton("🗑 Удалить товар", callback_data="admin_del_prod")],
        [InlineKeyboardButton("🗑 Удалить категорию", callback_data="admin_del_cat")],
        [InlineKeyboardButton("🎁 Создать промокод", callback_data="admin_add_promo")],
        [InlineKeyboardButton("📋 Промокоды", callback_data="admin_view_promos")],
        [InlineKeyboardButton("📋 Все заказы", callback_data="admin_view_orders")],
        [InlineKeyboardButton("❌ Закрыть", callback_data="admin_close")],
    ])


def order_status_keyboard(order_id: int, current_status: str):
    buttons = []
    row = []
    for key, label in STATUSES.items():
        if key == current_status:
            row.append(InlineKeyboardButton(f"· {label} ·", callback_data="noop"))
        else:
            row.append(InlineKeyboardButton(label, callback_data=f"set_status_{order_id}_{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("⬅️ К списку заказов", callback_data="admin_view_orders")])
    return InlineKeyboardMarkup(buttons)


def format_order_detail(order: dict) -> str:
    items = json.loads(order["items_json"])
    items_str = "\n".join(f"  • {i['name']} x{i['quantity']} — {i['price'] * i['quantity']:.2f} сомонӣ" for i in items)
    status_label = STATUSES.get(order["status"], order["status"])
    return (
        f"📦 *Заказ #{order['id']}* | {order['created_at'][:16]}\n\n"
        f"👤 {order['customer_name']}\n"
        f"📱 {order['phone']}\n"
        f"🏠 {order['address']}\n\n"
        f"🛍 Товары:\n{items_str}\n\n"
        f"💰 Итого: *{order['total']:.2f} сомонӣ*\n"
        f"📌 Статус: *{status_label}*\n\n"
        f"Выберите новый статус:"
    )


# --- Entry & Menu ---

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text(
            "⛔ У вас нет доступа к панели администратора.\n\n"
            "Попросите владельца бота добавить ваш Telegram ID в список администраторов."
        )
        return ConversationHandler.END

    sent = await update.message.reply_text(
        "👮 *Панель администратора*\n\nЧто вы хотите сделать?",
        parse_mode="Markdown",
        reply_markup=admin_menu_keyboard(),
    )
    context.user_data["apanel_msg"] = sent.message_id
    context.user_data["apanel_chat"] = update.effective_chat.id
    return ADMIN_MENU


async def admin_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["apanel_msg"] = query.message.message_id
    context.user_data["apanel_chat"] = query.message.chat_id
    await query.edit_message_text(
        "👮 *Панель администратора*\n\nЧто вы хотите сделать?",
        parse_mode="Markdown",
        reply_markup=admin_menu_keyboard(),
    )
    return ADMIN_MENU


async def admin_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Панель администратора закрыта.")
    return ConversationHandler.END


# --- Add Category ---

async def start_add_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["apanel_msg"] = query.message.message_id
    context.user_data["apanel_chat"] = query.message.chat_id
    await query.edit_message_text("📁 Введите *название категории*:", parse_mode="Markdown")
    return ADD_CAT_NAME


async def save_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    await database.add_category(name)
    try:
        await update.message.delete()
    except Exception:
        pass
    await context.bot.edit_message_text(
        chat_id=context.user_data["apanel_chat"],
        message_id=context.user_data["apanel_msg"],
        text=f"✅ Категория *{name}* добавлена!",
        parse_mode="Markdown",
        reply_markup=admin_menu_keyboard(),
    )
    return ADMIN_MENU


# --- Add Product ---

async def start_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["apanel_msg"] = query.message.message_id
    context.user_data["apanel_chat"] = query.message.chat_id

    categories = await database.get_categories()
    if not categories:
        await query.edit_message_text(
            "Категорий пока нет. Сначала добавьте категорию.",
            reply_markup=admin_menu_keyboard(),
        )
        return ADMIN_MENU

    buttons = [
        [InlineKeyboardButton(cat["name"], callback_data=f"admin_cat_{cat['id']}")]
        for cat in categories
    ]
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back_menu")])

    await query.edit_message_text(
        "Выберите *категорию* для товара:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return ADD_PROD_SELECT_CAT


async def select_product_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["apanel_msg"] = query.message.message_id
    context.user_data["apanel_chat"] = query.message.chat_id

    category_id = int(query.data.split("_")[2])
    context.user_data["new_product_category_id"] = category_id

    await query.edit_message_text("Введите *название товара*:", parse_mode="Markdown")
    return ADD_PROD_NAME


async def get_product_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_product_name"] = update.message.text.strip()
    try:
        await update.message.delete()
    except Exception:
        pass
    await context.bot.edit_message_text(
        chat_id=context.user_data["apanel_chat"],
        message_id=context.user_data["apanel_msg"],
        text="Введите *описание товара* (или отправьте /skip, чтобы пропустить):",
        parse_mode="Markdown",
    )
    return ADD_PROD_DESC


async def get_product_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_product_desc"] = update.message.text.strip()
    try:
        await update.message.delete()
    except Exception:
        pass
    await context.bot.edit_message_text(
        chat_id=context.user_data["apanel_chat"],
        message_id=context.user_data["apanel_msg"],
        text="Введите *цену* (например: 999.99):",
        parse_mode="Markdown",
    )
    return ADD_PROD_PRICE


async def skip_product_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_product_desc"] = ""
    try:
        await update.message.delete()
    except Exception:
        pass
    await context.bot.edit_message_text(
        chat_id=context.user_data["apanel_chat"],
        message_id=context.user_data["apanel_msg"],
        text="Введите *цену* (например: 999.99):",
        parse_mode="Markdown",
    )
    return ADD_PROD_PRICE


async def get_product_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", ".")
    try:
        price = float(text)
    except ValueError:
        try:
            await update.message.delete()
        except Exception:
            pass
        await context.bot.edit_message_text(
            chat_id=context.user_data["apanel_chat"],
            message_id=context.user_data["apanel_msg"],
            text="❌ Введите корректное число, например: *999.99*\n\nВведите *цену*:",
            parse_mode="Markdown",
        )
        return ADD_PROD_PRICE

    context.user_data["new_product_price"] = price
    try:
        await update.message.delete()
    except Exception:
        pass
    await context.bot.edit_message_text(
        chat_id=context.user_data["apanel_chat"],
        message_id=context.user_data["apanel_msg"],
        text="Отправьте *фото* товара (или /skip, чтобы добавить без фото):",
        parse_mode="Markdown",
    )
    return ADD_PROD_PHOTO


async def get_product_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    photo = update.message.photo[-1]
    context.user_data["new_product_photo"] = photo.file_id
    return await _save_product(update, context)


async def skip_product_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_product_photo"] = None
    return await _save_product(update, context)


async def _save_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cat_id = context.user_data["new_product_category_id"]
    name = context.user_data["new_product_name"]
    desc = context.user_data.get("new_product_desc", "")
    price = context.user_data["new_product_price"]
    photo = context.user_data.get("new_product_photo")

    await database.add_product(cat_id, name, desc, price, photo)

    for key in ["new_product_category_id", "new_product_name", "new_product_desc",
                "new_product_price", "new_product_photo"]:
        context.user_data.pop(key, None)

    try:
        await update.message.delete()
    except Exception:
        pass
    await context.bot.edit_message_text(
        chat_id=context.user_data["apanel_chat"],
        message_id=context.user_data["apanel_msg"],
        text=f"✅ Товар *{name}* добавлен по цене {price:.2f} сомонӣ!",
        parse_mode="Markdown",
        reply_markup=admin_menu_keyboard(),
    )
    return ADMIN_MENU


# --- Orders List ---

async def view_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    orders = await database.get_all_orders()
    if not orders:
        await query.edit_message_text(
            "Заказов пока нет.",
            reply_markup=admin_menu_keyboard(),
        )
        return ADMIN_MENU

    buttons = []
    for order in orders[:30]:
        status_label = STATUSES.get(order["status"], order["status"])
        buttons.append([
            InlineKeyboardButton(
                f"#{order['id']} | {order['customer_name']} | {status_label}",
                callback_data=f"admin_order_{order['id']}",
            )
        ])
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back_menu")])

    await query.edit_message_text(
        "📋 *Список заказов:*\nНажмите на заказ, чтобы изменить статус.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return ORDER_DETAIL


# --- Order Detail & Status Change ---

async def admin_order_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    order_id = int(query.data.split("_")[2])
    order = await database.get_order(order_id)
    if not order:
        await query.edit_message_text("Заказ не найден.")
        return ORDER_DETAIL

    await query.edit_message_text(
        format_order_detail(order),
        parse_mode="Markdown",
        reply_markup=order_status_keyboard(order_id, order["status"]),
    )
    return ORDER_DETAIL


async def change_order_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")
    order_id = int(parts[2])
    new_status = parts[3]

    await database.update_order_status(order_id, new_status)
    order = await database.get_order(order_id)

    notify_text = STATUS_NOTIFY.get(new_status)
    if notify_text and order:
        try:
            await context.bot.send_message(
                chat_id=order["user_id"],
                text=notify_text.replace("{id}", str(order_id)),
                parse_mode="Markdown",
            )
        except Exception:
            pass

    await query.edit_message_text(
        format_order_detail(order),
        parse_mode="Markdown",
        reply_markup=order_status_keyboard(order_id, new_status),
    )
    return ORDER_DETAIL


async def noop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()


# --- Delete Product ---

async def start_del_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    categories = await database.get_categories()
    if not categories:
        await query.edit_message_text(
            "Категорий пока нет.",
            reply_markup=admin_menu_keyboard(),
        )
        return ADMIN_MENU

    buttons = [
        [InlineKeyboardButton(cat["name"], callback_data=f"delprod_cat_{cat['id']}")]
        for cat in categories
    ]
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back_menu")])
    await query.edit_message_text(
        "🗑 *Удаление товара*\n\nВыберите категорию:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return DEL_PROD_SELECT_CAT


async def del_product_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_id = int(query.data.split("_")[2])
    context.user_data["del_prod_cat_id"] = cat_id
    products = await database.get_products_by_category(cat_id)

    if not products:
        await query.edit_message_text(
            "В этой категории нет товаров.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Назад", callback_data="admin_del_prod")]
            ]),
        )
        return DEL_PROD_SELECT_CAT

    buttons = [
        [
            InlineKeyboardButton(p["name"], callback_data="noop"),
            InlineKeyboardButton("🗑", callback_data=f"delprod_ask_{p['id']}"),
        ]
        for p in products
    ]
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_del_prod")])
    await query.edit_message_text(
        "🗑 *Список товаров* — нажмите 🗑 рядом с товаром для удаления:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return DEL_PROD_LIST


async def del_product_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    prod_id = int(query.data.split("_")[2])
    product = await database.get_product(prod_id)
    if not product:
        await query.answer("Товар не найден.", show_alert=True)
        return DEL_PROD_LIST

    context.user_data["del_prod_id"] = prod_id
    await query.edit_message_text(
        f"❓ *Вы уверены?*\n\nУдалить товар *{product['name']}*?\n"
        f"Это также удалит его из корзин пользователей.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Да, удалить", callback_data=f"delprod_yes_{prod_id}"),
                InlineKeyboardButton("❌ Отмена", callback_data=f"delprod_no"),
            ]
        ]),
    )
    return DEL_PROD_LIST


async def del_product_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    prod_id = int(query.data.split("_")[2])
    await database.delete_product(prod_id)

    cat_id = context.user_data.get("del_prod_cat_id")
    products = await database.get_products_by_category(cat_id) if cat_id else []

    if not products:
        await query.edit_message_text(
            "✅ Товар удалён. В этой категории больше нет товаров.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ К категориям", callback_data="admin_del_prod")]
            ]),
        )
        return DEL_PROD_SELECT_CAT

    buttons = [
        [
            InlineKeyboardButton(p["name"], callback_data="noop"),
            InlineKeyboardButton("🗑", callback_data=f"delprod_ask_{p['id']}"),
        ]
        for p in products
    ]
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_del_prod")])
    await query.edit_message_text(
        "✅ Товар удалён.\n\n🗑 *Список товаров* — нажмите 🗑 для удаления:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return DEL_PROD_LIST


async def del_product_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_id = context.user_data.get("del_prod_cat_id")
    products = await database.get_products_by_category(cat_id) if cat_id else []

    buttons = [
        [
            InlineKeyboardButton(p["name"], callback_data="noop"),
            InlineKeyboardButton("🗑", callback_data=f"delprod_ask_{p['id']}"),
        ]
        for p in products
    ]
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_del_prod")])
    await query.edit_message_text(
        "🗑 *Список товаров* — нажмите 🗑 рядом с товаром для удаления:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return DEL_PROD_LIST


# --- Delete Category ---

async def start_del_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    return await _show_del_cat_list(query, context)


async def _show_del_cat_list(query, context):
    categories = await database.get_categories()
    if not categories:
        await query.edit_message_text(
            "Категорий пока нет.",
            reply_markup=admin_menu_keyboard(),
        )
        return ADMIN_MENU

    buttons = [
        [
            InlineKeyboardButton(cat["name"], callback_data="noop"),
            InlineKeyboardButton("🗑", callback_data=f"delcat_ask_{cat['id']}"),
        ]
        for cat in categories
    ]
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back_menu")])
    await query.edit_message_text(
        "🗑 *Удаление категории* — нажмите 🗑 рядом с категорией:\n\n"
        "⚠️ Вместе с категорией будут удалены все её товары.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return DEL_CAT_LIST


async def del_category_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_id = int(query.data.split("_")[2])
    category = await database.get_category(cat_id)
    if not category:
        await query.answer("Категория не найдена.", show_alert=True)
        return DEL_CAT_LIST

    products = await database.get_products_by_category(cat_id)
    prod_count = len(products)
    warning = f"\nВ ней {prod_count} товар(ов), они тоже будут удалены." if prod_count else ""

    await query.edit_message_text(
        f"❓ *Вы уверены?*\n\nУдалить категорию *{category['name']}*?{warning}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Да, удалить", callback_data=f"delcat_yes_{cat_id}"),
                InlineKeyboardButton("❌ Отмена", callback_data="delcat_no"),
            ]
        ]),
    )
    return DEL_CAT_LIST


async def del_category_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_id = int(query.data.split("_")[2])
    await database.delete_category(cat_id)

    categories = await database.get_categories()
    if not categories:
        await query.edit_message_text(
            "✅ Категория удалена. Больше нет категорий.",
            reply_markup=admin_menu_keyboard(),
        )
        return ADMIN_MENU

    buttons = [
        [
            InlineKeyboardButton(cat["name"], callback_data="noop"),
            InlineKeyboardButton("🗑", callback_data=f"delcat_ask_{cat['id']}"),
        ]
        for cat in categories
    ]
    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back_menu")])
    await query.edit_message_text(
        "✅ Категория удалена.\n\n🗑 *Удаление категории* — нажмите 🗑 рядом с категорией:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return DEL_CAT_LIST


async def del_category_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    return await _show_del_cat_list(query, context)


# --- Promo Codes ---

async def start_add_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["apanel_msg"] = query.message.message_id
    context.user_data["apanel_chat"] = query.message.chat_id
    await query.edit_message_text(
        "🎁 *Создание промокода*\n\nВведите *код* (например: SUMMER50):",
        parse_mode="Markdown",
    )
    return ADD_PROMO_CODE


async def save_promo_code_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper()
    context.user_data["new_promo_code"] = code
    try:
        await update.message.delete()
    except Exception:
        pass
    await context.bot.edit_message_text(
        chat_id=context.user_data["apanel_chat"],
        message_id=context.user_data["apanel_msg"],
        text=f"🎁 Код: *{code}*\n\nВведите *баланс* в сомонӣ (например: 50):",
        parse_mode="Markdown",
    )
    return ADD_PROMO_BALANCE


async def save_promo_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace(",", ".")
    try:
        balance = float(text)
        if balance <= 0:
            raise ValueError
    except ValueError:
        try:
            await update.message.delete()
        except Exception:
            pass
        await context.bot.edit_message_text(
            chat_id=context.user_data["apanel_chat"],
            message_id=context.user_data["apanel_msg"],
            text="❌ Введите корректную сумму (больше 0), например: *50*\n\nВведите *баланс*:",
            parse_mode="Markdown",
        )
        return ADD_PROMO_BALANCE

    code = context.user_data.pop("new_promo_code", "")
    try:
        await update.message.delete()
    except Exception:
        pass

    existing = await database.get_promo_code_by_code(code)
    if existing:
        await context.bot.edit_message_text(
            chat_id=context.user_data["apanel_chat"],
            message_id=context.user_data["apanel_msg"],
            text=f"❌ Промокод *{code}* уже существует!\n\nВведите другой код:",
            parse_mode="Markdown",
        )
        return ADD_PROMO_CODE

    await database.create_promo_code(code, balance)
    await context.bot.edit_message_text(
        chat_id=context.user_data["apanel_chat"],
        message_id=context.user_data["apanel_msg"],
        text=f"✅ Промокод *{code}* на *{balance:.2f} сомонӣ* создан!",
        parse_mode="Markdown",
        reply_markup=admin_menu_keyboard(),
    )
    return ADMIN_MENU


async def view_promos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["apanel_msg"] = query.message.message_id
    context.user_data["apanel_chat"] = query.message.chat_id
    return await _show_promo_list(query, context)


async def _show_promo_list(query, context):
    promos = await database.get_all_promo_codes()
    if not promos:
        await query.edit_message_text(
            "🎁 Промокодов пока нет.",
            reply_markup=admin_menu_keyboard(),
        )
        return ADMIN_MENU

    buttons = []
    for p in promos:
        status = "❌ Использован" if p["is_used"] else "✅ Активен"
        label = f"{p['code']} | {p['balance']:.2f} сом. | {status}"
        row = [InlineKeyboardButton(label, callback_data="noop")]
        if not p["is_used"]:
            row.append(InlineKeyboardButton("🗑", callback_data=f"delpromo_ask_{p['id']}"))
        buttons.append(row)

    buttons.append([InlineKeyboardButton("⬅️ Назад", callback_data="admin_back_menu")])
    await query.edit_message_text(
        "🎁 *Список промокодов:*\n\nНажмите 🗑 чтобы удалить активный промокод.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return PROMO_LIST


async def del_promo_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    promo_id = int(query.data.split("_")[2])
    promos = await database.get_all_promo_codes()
    promo = next((p for p in promos if p["id"] == promo_id), None)
    if not promo:
        await query.answer("Промокод не найден.", show_alert=True)
        return PROMO_LIST

    await query.edit_message_text(
        f"❓ *Вы уверены?*\n\nУдалить промокод *{promo['code']}* ({promo['balance']:.2f} сомонӣ)?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Да, удалить", callback_data=f"delpromo_yes_{promo_id}"),
                InlineKeyboardButton("❌ Отмена", callback_data="delpromo_no"),
            ]
        ]),
    )
    return PROMO_LIST


async def del_promo_execute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    promo_id = int(query.data.split("_")[2])
    await database.delete_promo_code(promo_id)
    return await _show_promo_list(query, context)


async def del_promo_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    return await _show_promo_list(query, context)


# --- Cancel & Fallback ---

async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("Действие отменено.")
    return ConversationHandler.END


def admin_conv_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("admin", admin_command)],
        states={
            ADMIN_MENU: [
                CallbackQueryHandler(start_add_category, pattern="^admin_add_cat$"),
                CallbackQueryHandler(start_add_product, pattern="^admin_add_prod$"),
                CallbackQueryHandler(start_del_product, pattern="^admin_del_prod$"),
                CallbackQueryHandler(start_del_category, pattern="^admin_del_cat$"),
                CallbackQueryHandler(start_add_promo, pattern="^admin_add_promo$"),
                CallbackQueryHandler(view_promos, pattern="^admin_view_promos$"),
                CallbackQueryHandler(view_orders, pattern="^admin_view_orders$"),
                CallbackQueryHandler(admin_close, pattern="^admin_close$"),
            ],
            ADD_CAT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_category),
            ],
            ADD_PROD_SELECT_CAT: [
                CallbackQueryHandler(select_product_category, pattern="^admin_cat_\\d+$"),
                CallbackQueryHandler(admin_menu_callback, pattern="^admin_back_menu$"),
            ],
            ADD_PROD_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_product_name),
            ],
            ADD_PROD_DESC: [
                CommandHandler("skip", skip_product_desc),
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_product_desc),
            ],
            ADD_PROD_PRICE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_product_price),
            ],
            ADD_PROD_PHOTO: [
                CommandHandler("skip", skip_product_photo),
                MessageHandler(filters.PHOTO, get_product_photo),
            ],
            ORDER_DETAIL: [
                CallbackQueryHandler(admin_order_detail, pattern="^admin_order_\\d+$"),
                CallbackQueryHandler(change_order_status, pattern="^set_status_\\d+_\\w+$"),
                CallbackQueryHandler(view_orders, pattern="^admin_view_orders$"),
                CallbackQueryHandler(admin_menu_callback, pattern="^admin_back_menu$"),
                CallbackQueryHandler(noop_callback, pattern="^noop$"),
            ],
            DEL_PROD_SELECT_CAT: [
                CallbackQueryHandler(del_product_list, pattern="^delprod_cat_\\d+$"),
                CallbackQueryHandler(start_del_product, pattern="^admin_del_prod$"),
                CallbackQueryHandler(admin_menu_callback, pattern="^admin_back_menu$"),
            ],
            DEL_PROD_LIST: [
                CallbackQueryHandler(del_product_confirm, pattern="^delprod_ask_\\d+$"),
                CallbackQueryHandler(del_product_execute, pattern="^delprod_yes_\\d+$"),
                CallbackQueryHandler(del_product_cancel, pattern="^delprod_no$"),
                CallbackQueryHandler(start_del_product, pattern="^admin_del_prod$"),
                CallbackQueryHandler(noop_callback, pattern="^noop$"),
            ],
            DEL_CAT_LIST: [
                CallbackQueryHandler(del_category_confirm, pattern="^delcat_ask_\\d+$"),
                CallbackQueryHandler(del_category_execute, pattern="^delcat_yes_\\d+$"),
                CallbackQueryHandler(del_category_cancel, pattern="^delcat_no$"),
                CallbackQueryHandler(admin_menu_callback, pattern="^admin_back_menu$"),
                CallbackQueryHandler(noop_callback, pattern="^noop$"),
            ],
            ADD_PROMO_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_promo_code_name),
            ],
            ADD_PROMO_BALANCE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_promo_balance),
            ],
            PROMO_LIST: [
                CallbackQueryHandler(del_promo_confirm, pattern="^delpromo_ask_\\d+$"),
                CallbackQueryHandler(del_promo_execute, pattern="^delpromo_yes_\\d+$"),
                CallbackQueryHandler(del_promo_cancel, pattern="^delpromo_no$"),
                CallbackQueryHandler(admin_menu_callback, pattern="^admin_back_menu$"),
                CallbackQueryHandler(noop_callback, pattern="^noop$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_admin)],
        per_message=False,
    )
