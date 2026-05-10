from telegram import InlineKeyboardMarkup


async def safe_edit_text(query, text: str, reply_markup: InlineKeyboardMarkup = None, parse_mode: str = None):
    """
    Edit a message's text. If the message is a photo/media message,
    delete it and send a fresh text message instead.
    """
    kwargs = {"reply_markup": reply_markup}
    if parse_mode:
        kwargs["parse_mode"] = parse_mode

    try:
        await query.edit_message_text(text, **kwargs)
    except Exception:
        try:
            await query.message.delete()
        except Exception:
            pass
        await query.message.chat.send_message(text, **kwargs)
