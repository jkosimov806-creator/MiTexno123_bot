import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    CommandHandler,
)

import database

NAME, PHONE, ADDRESS, CONFIRM, PROMO_CODE, PROMO_PRODUCT, WALLET_PRODUCT = range(7)


async def start_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    items = await database.get_cart(user_id)

    if not items:
        await query.edit_message_text(
            "Ваша корзина пуста.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")]
            ]),
        )
        return ConversationHandler.END

    context.user_data["checkout_items"] = items
    context.user_data["checkout_total"] = sum(i["price"] * i["quantity"] for i in items)
    context.user_data["checkout_user_id"] = user_id

    await query.edit_message_text(
        "📋 *Оформление заказа*\n\nВведите ваше *полное имя*:",
        parse_mode="Markdown",
    )
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["checkout_name"] = update.message.text.strip()
    await update.message.reply_text("📱 Введите ваш *номер телефона*:", parse_mode="Markdown")
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip()
    compact = phone.replace(" ", "").replace("-", "")
    digits_after_code = compact[4:] if compact.startswith("+992") else ""
    if not compact.startswith("+992") or not digits_after_code.isdigit() or len(digits_after_code) != 9:
        await update.message.reply_text(
            "❌ Неверный формат номера.\n\n"
            "Номер должен начинаться с *+992* и содержать ровно 9 цифр после него.\n"
            "Пример: *+992 12 345 67 89*\n\n"
            "Попробуйте ещё раз:",
            parse_mode="Markdown",
        )
        return PHONE
    context.user_data["checkout_phone"] = phone
    await update.message.reply_text(
        "🏠 Введите ваш *адрес доставки*\n\nДоставка ТОЛЬКО по Худжанду бесплатна ❕",
        parse_mode="Markdown",
    )
    return ADDRESS


async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["checkout_address"] = update.message.text.strip()
    user_id = update.message.from_user.id
    wallet_balance = await database.get_wallet_balance(user_id)
    context.user_data["wallet_balance_at_checkout"] = wallet_balance
    await _show_confirm(update, context, via_callback=False)
    return CONFIRM


async def _show_confirm(update, context, via_callback=False):
    items = context.user_data["checkout_items"]
    total = context.user_data["checkout_total"]
    name = context.user_data["checkout_name"]
    phone = context.user_data["checkout_phone"]
    address = context.user_data["checkout_address"]

    promo_discount = context.user_data.get("promo_discount", 0)
    promo_code_str = context.user_data.get("promo_code", "")
    promo_product_name = context.user_data.get("promo_product_name", "")

    wallet_discount = context.user_data.get("wallet_discount", 0)
    wallet_product_name = context.user_data.get("wallet_product_name", "")
    wallet_balance = context.user_data.get("wallet_balance_at_checkout", 0)

    lines = "\n".join(
        f"• {i['name']} x{i['quantity']} — {i['price'] * i['quantity']:.2f} сомонӣ"
        for i in items
    )

    total_discount = promo_discount + wallet_discount
    final_total = max(0.0, total - total_discount)

    discount_lines = ""
    if promo_discount > 0:
        discount_lines += (
            f"\n🎁 Промокод *{promo_code_str}*: −{promo_discount:.2f} сомонӣ\n"
            f"   (скидка на «{promo_product_name}»)"
        )
    if wallet_discount > 0:
        discount_lines += (
            f"\n👛 Кошелёк: −{wallet_discount:.2f} сомонӣ\n"
            f"   (скидка на «{wallet_product_name}»)"
        )

    if total_discount > 0:
        total_line = f"💰 *Итого со скидкой: {final_total:.2f} сомонӣ*"
    else:
        total_line = f"💰 *Итого: {total:.2f} сомонӣ*"

    text = (
        f"📋 *Ваш заказ:*\n\n"
        f"{lines}\n\n"
        f"{total_line}{discount_lines}\n\n"
        f"👤 Имя: {name}\n"
        f"📱 Телефон: {phone}\n"
        f"🏠 Адрес: {address}\n\n"
        f"Подтвердить заказ?"
    )

    if promo_discount > 0:
        promo_btn = InlineKeyboardButton("✏️ Изменить промокод", callback_data="apply_promo")
    else:
        promo_btn = InlineKeyboardButton("🎁 Применить промокод", callback_data="apply_promo")

    buttons = [
        [
            InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_order"),
            InlineKeyboardButton("❌ Отмена", callback_data="cancel_order"),
        ],
        [promo_btn],
    ]

    if wallet_balance > 0 and wallet_discount == 0:
        buttons.append([
            InlineKeyboardButton(
                f"👛 Использовать баланс ({wallet_balance:.2f} сом.)",
                callback_data="apply_wallet",
            )
        ])
    elif wallet_discount > 0:
        buttons.append([
            InlineKeyboardButton("✏️ Изменить баланс", callback_data="apply_wallet")
        ])

    keyboard = InlineKeyboardMarkup(buttons)

    if via_callback:
        query = update.callback_query
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=keyboard)
    else:
        sent = await update.message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)
        context.user_data["checkout_msg"] = sent.message_id
        context.user_data["checkout_chat"] = update.message.chat_id


# ── Promo code flow ────────────────────────────────────────────────────────────

async def start_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    for key in ["promo_code", "promo_balance", "promo_code_id",
                "promo_discount", "promo_product_name", "promo_product_idx"]:
        context.user_data.pop(key, None)

    context.user_data["checkout_msg"] = query.message.message_id
    context.user_data["checkout_chat"] = query.message.chat_id

    await query.edit_message_text(
        "🎁 Введите *промокод*:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel_promo")]
        ]),
    )
    return PROMO_CODE


async def get_promo_code_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper()
    try:
        await update.message.delete()
    except Exception:
        pass

    promo = await database.get_promo_code_by_code(code)

    if not promo or promo["is_used"]:
        await context.bot.edit_message_text(
            chat_id=context.user_data["checkout_chat"],
            message_id=context.user_data["checkout_msg"],
            text=f"❌ Промокод *{code}* недействителен или уже использован.\n\nВведите другой промокод:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Отмена", callback_data="cancel_promo")]
            ]),
        )
        return PROMO_CODE

    context.user_data["promo_code"] = promo["code"]
    context.user_data["promo_balance"] = promo["balance"]
    context.user_data["promo_code_id"] = promo["id"]

    items = context.user_data["checkout_items"]
    buttons = [
        [InlineKeyboardButton(
            f"{i['name']} x{i['quantity']} — {i['price'] * i['quantity']:.2f} сомонӣ",
            callback_data=f"promo_prod_{idx}",
        )]
        for idx, i in enumerate(items)
    ]
    buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_promo")])

    await context.bot.edit_message_text(
        chat_id=context.user_data["checkout_chat"],
        message_id=context.user_data["checkout_msg"],
        text=(
            f"✅ Промокод *{promo['code']}* на *{promo['balance']:.2f} сомонӣ* принят!\n\n"
            f"Выберите товар, к которому применить скидку:"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return PROMO_PRODUCT


async def select_promo_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = int(query.data.split("_")[2])
    items = context.user_data["checkout_items"]
    item = items[idx]

    promo_balance = context.user_data["promo_balance"]
    item_total = item["price"] * item["quantity"]
    discount = min(promo_balance, item_total)

    context.user_data["promo_discount"] = discount
    context.user_data["promo_product_name"] = item["name"]
    context.user_data["promo_product_idx"] = idx

    await _show_confirm(update, context, via_callback=True)
    return CONFIRM


async def cancel_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    for key in ["promo_code", "promo_balance", "promo_code_id",
                "promo_discount", "promo_product_name", "promo_product_idx"]:
        context.user_data.pop(key, None)

    await _show_confirm(update, context, via_callback=True)
    return CONFIRM


# ── Wallet balance flow ────────────────────────────────────────────────────────

async def start_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    for key in ["wallet_discount", "wallet_product_name", "wallet_product_idx"]:
        context.user_data.pop(key, None)

    context.user_data["checkout_msg"] = query.message.message_id
    context.user_data["checkout_chat"] = query.message.chat_id

    wallet_balance = context.user_data.get("wallet_balance_at_checkout", 0)
    items = context.user_data["checkout_items"]

    buttons = [
        [InlineKeyboardButton(
            f"{i['name']} x{i['quantity']} — {i['price'] * i['quantity']:.2f} сомонӣ",
            callback_data=f"wallet_prod_{idx}",
        )]
        for idx, i in enumerate(items)
    ]
    buttons.append([InlineKeyboardButton("❌ Отмена", callback_data="cancel_wallet")])

    await query.edit_message_text(
        f"👛 Ваш баланс: *{wallet_balance:.2f} сомонӣ*\n\n"
        f"Выберите товар, к которому применить скидку из кошелька:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
    return WALLET_PRODUCT


async def select_wallet_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    idx = int(query.data.split("_")[2])
    items = context.user_data["checkout_items"]
    item = items[idx]

    wallet_balance = context.user_data.get("wallet_balance_at_checkout", 0)
    item_total = item["price"] * item["quantity"]
    discount = min(wallet_balance, item_total)

    context.user_data["wallet_discount"] = discount
    context.user_data["wallet_product_name"] = item["name"]
    context.user_data["wallet_product_idx"] = idx

    await _show_confirm(update, context, via_callback=True)
    return CONFIRM


async def cancel_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    for key in ["wallet_discount", "wallet_product_name", "wallet_product_idx"]:
        context.user_data.pop(key, None)

    await _show_confirm(update, context, via_callback=True)
    return CONFIRM


# ── Confirm / Cancel ───────────────────────────────────────────────────────────

async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    items = context.user_data["checkout_items"]
    total = context.user_data["checkout_total"]
    name = context.user_data["checkout_name"]
    phone = context.user_data["checkout_phone"]
    address = context.user_data["checkout_address"]

    promo_discount = context.user_data.get("promo_discount", 0)
    promo_code_id = context.user_data.get("promo_code_id")
    promo_code_str = context.user_data.get("promo_code", "")
    promo_product_name = context.user_data.get("promo_product_name", "")

    wallet_discount = context.user_data.get("wallet_discount", 0)
    wallet_product_name = context.user_data.get("wallet_product_name", "")

    total_discount = promo_discount + wallet_discount
    final_total = max(0.0, total - total_discount)

    order_id = await database.create_order(
        user_id=user_id,
        customer_name=name,
        phone=phone,
        address=address,
        items=[{"name": i["name"], "quantity": i["quantity"], "price": i["price"]} for i in items],
        total=final_total,
    )
    await database.clear_cart(user_id)

    if promo_code_id:
        await database.use_promo_code(promo_code_id, user_id)

    if wallet_discount > 0:
        await database.deduct_from_wallet(user_id, wallet_discount)

    context.user_data.clear()

    card_number = os.environ.get("CARD_NUMBER", "не указан")

    notes = []
    if promo_discount > 0:
        notes.append(
            f"🎁 Промокод *{promo_code_str}*: −{promo_discount:.2f} сомонӣ на «{promo_product_name}»"
        )
    if wallet_discount > 0:
        notes.append(
            f"👛 Кошелёк: −{wallet_discount:.2f} сомонӣ на «{wallet_product_name}»"
        )
    note_text = ("\n" + "\n".join(notes)) if notes else ""

    await query.edit_message_text(
        f"✅ *Заказ #{order_id} оформлен!*{note_text}\n\n"
        f"Переведите *{final_total:.2f} сомонӣ* на номер карты:\n\n"
        f"💳 `{card_number}`\n\n"
        f"После оплаты нажмите кнопку *«Я оплатил»*.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Я оплатил", callback_data=f"paid_{order_id}")],
        ]),
    )
    return ConversationHandler.END


async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data.clear()

    await query.edit_message_text(
        "Заказ отменён. Ваша корзина сохранена.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Вернуться в корзину", callback_data="show_cart")],
            [InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")],
        ]),
    )
    return ConversationHandler.END


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Действие отменено.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")]
        ]),
    )
    return ConversationHandler.END


def checkout_conv_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_checkout, pattern="^checkout$")],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            CONFIRM: [
                CallbackQueryHandler(confirm_order, pattern="^confirm_order$"),
                CallbackQueryHandler(cancel_order, pattern="^cancel_order$"),
                CallbackQueryHandler(start_promo, pattern="^apply_promo$"),
                CallbackQueryHandler(start_wallet, pattern="^apply_wallet$"),
            ],
            PROMO_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, get_promo_code_input),
                CallbackQueryHandler(cancel_promo, pattern="^cancel_promo$"),
            ],
            PROMO_PRODUCT: [
                CallbackQueryHandler(select_promo_product, pattern="^promo_prod_\\d+$"),
                CallbackQueryHandler(cancel_promo, pattern="^cancel_promo$"),
            ],
            WALLET_PRODUCT: [
                CallbackQueryHandler(select_wallet_product, pattern="^wallet_prod_\\d+$"),
                CallbackQueryHandler(cancel_wallet, pattern="^cancel_wallet$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_command)],
        per_message=False,
    )
