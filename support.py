from aiogram import Router, F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import SUPPORT_USERNAME

router = Router()


@router.callback_query(F.data == "support")
async def support_info(c: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.button(text="💬 Написать менеджеру", url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")
    kb.button(text="⬅️ На главную", callback_data="to_main")
    kb.adjust(1)

    await c.message.edit_text(
        "<b>🛡 СЛУЖБА ПОДДЕРЖКИ MI TEXNO</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Наши специалисты помогут вам с выбором и оформлением заказа.\n\n"
        f"👉 Менеджер: {SUPPORT_USERNAME}\n"
        "🕐 Режим работы: 9:00 – 22:00",
        reply_markup=kb.as_markup(),
        parse_mode="HTML",
    )
