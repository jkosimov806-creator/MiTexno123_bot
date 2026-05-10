import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

import database
from config import get_admin_ids


async def paid_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    order_id = int(query.data.split("_")[1])
    order = await database.get_order(order_id)

    if not order:
        await query.edit_message_text("Заказ не найден.")
        return

    await query.edit_message_text(
        f"⏳ *Оплата по заказу #{order_id} отправлена на проверку.*\n\n"
        f"Администратор подтвердит вашу оплату в ближайшее время.",
        parse_mode="Markdown",
    )

    items = json.loads(order["items_json"])
    items_text = "\n".join(
        f"  • {i['name']} x{i['quantity']} — {i['price'] * i['quantity']:.2f} сомонӣ"
        for i in items
    )
    admin_text = (
        f"💳 *Клиент сообщил об оплате заказа #{order_id}*\n\n"
        f"👤 {order['customer_name']}\n"
        f"📱 {order['phone']}\n"
        f"🏠 {order['address']}\n\n"
        f"🛍 Товары:\n{items_text}\n\n"
        f"💰 Сумма: *{order['total']:.2f} сомонӣ*\n\n"
        f"Клиент сообщил об оплате, проверьте перевод."
    )

    for admin_id in get_admin_ids():
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Подтвердить", callback_data=f"admin_confirm_{order_id}"),
                        InlineKeyboardButton("❌ Отменить", callback_data=f"admin_cancel_{order_id}"),
                    ]
                ]),
            )
        except Exception:
            pass


async def admin_confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    order_id = int(query.data.split("_")[2])
    order = await database.get_order(order_id)
    if not order:
        return

    await database.update_order_status(order_id, "confirmed")

    try:
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                f"✅ *Ваш заказ #{order_id} подтверждён, ожидайте доставку.*\n\n"
                f"Спасибо за покупку!"
            ),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")]
            ]),
        )
    except Exception:
        pass

    await query.edit_message_text(
        query.message.text + "\n\n✅ *Оплата подтверждена. Заказ передан в доставку.*",
        parse_mode="Markdown",
    )


async def admin_cancel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    order_id = int(query.data.split("_")[2])
    order = await database.get_order(order_id)
    if not order:
        return

    await database.update_order_status(order_id, "cancelled")

    try:
        await context.bot.send_message(
            chat_id=order["user_id"],
            text=(
                f"❌ *Оплата не найдена по заказу #{order_id}.*\n\n"
                f"Свяжитесь с нами для уточнения."
            ),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")]
            ]),
        )
    except Exception:
        pass

    await query.edit_message_text(
        query.message.text + "\n\n❌ *Заказ отменён.*",
        parse_mode="Markdown",
    )


def get_payment_handlers():
    return [
        CallbackQueryHandler(paid_handler, pattern="^paid_\\d+$"),
        CallbackQueryHandler(admin_confirm_handler, pattern="^admin_confirm_\\d+$"),
        CallbackQueryHandler(admin_cancel_handler, pattern="^admin_cancel_\\d+$"),
    ]
