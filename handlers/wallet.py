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

WALLET_CODE = 0


async def show_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    balance = await database.get_wallet_balance(user_id)
    context.user_data["wallet_msg"] = query.message.message_id
    context.user_data["wallet_chat"] = query.message.chat_id
    await query.edit_message_text(
        f"👛 *Ваш кошелёк*\n\n"
        f"💰 Баланс: *{balance:.2f} сомонӣ*\n\n"
        f"Введите промокод, чтобы пополнить баланс.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Ввести промокод", callback_data="wallet_enter_promo")],
            [InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")],
        ]),
    )
    return ConversationHandler.END


async def start_enter_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["wallet_msg"] = query.message.message_id
    context.user_data["wallet_chat"] = query.message.chat_id
    await query.edit_message_text(
        "🎁 Введите *промокод* для пополнения кошелька:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❌ Отмена", callback_data="wallet_cancel_promo")],
        ]),
    )
    return WALLET_CODE


async def process_wallet_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    code = update.message.text.strip().upper()
    user_id = update.message.from_user.id

    try:
        await update.message.delete()
    except Exception:
        pass

    promo = await database.get_promo_code_by_code(code)

    if not promo or promo["is_used"]:
        await context.bot.edit_message_text(
            chat_id=context.user_data["wallet_chat"],
            message_id=context.user_data["wallet_msg"],
            text=f"❌ Промокод *{code}* недействителен или уже использован.\n\nВведите другой промокод:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ Отмена", callback_data="wallet_cancel_promo")],
            ]),
        )
        return WALLET_CODE

    await database.use_promo_code(promo["id"], user_id)
    await database.add_to_wallet(user_id, promo["balance"])
    new_balance = await database.get_wallet_balance(user_id)

    await context.bot.edit_message_text(
        chat_id=context.user_data["wallet_chat"],
        message_id=context.user_data["wallet_msg"],
        text=(
            f"✅ Промокод *{promo['code']}* активирован!\n"
            f"На ваш кошелёк зачислено *{promo['balance']:.2f} сомонӣ*.\n\n"
            f"👛 Текущий баланс: *{new_balance:.2f} сомонӣ*"
        ),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Ввести ещё промокод", callback_data="wallet_enter_promo")],
            [InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")],
        ]),
    )
    return ConversationHandler.END


async def cancel_wallet_promo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    balance = await database.get_wallet_balance(user_id)
    await query.edit_message_text(
        f"👛 *Ваш кошелёк*\n\n"
        f"💰 Баланс: *{balance:.2f} сомонӣ*\n\n"
        f"Введите промокод, чтобы пополнить баланс.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🎁 Ввести промокод", callback_data="wallet_enter_promo")],
            [InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")],
        ]),
    )
    return ConversationHandler.END


async def cancel_wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "Действие отменено.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")]
        ]),
    )
    return ConversationHandler.END


def wallet_conv_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(show_wallet, pattern="^show_wallet$")],
        states={
            WALLET_CODE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_wallet_promo),
                CallbackQueryHandler(cancel_wallet_promo, pattern="^wallet_cancel_promo$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_wallet_command),
            CallbackQueryHandler(show_wallet, pattern="^show_wallet$"),
        ],
        per_message=False,
    )


def wallet_standalone_handlers():
    return [
        CallbackQueryHandler(start_enter_promo, pattern="^wallet_enter_promo$"),
        CallbackQueryHandler(cancel_wallet_promo, pattern="^wallet_cancel_promo$"),
    ]
