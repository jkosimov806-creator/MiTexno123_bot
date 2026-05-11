from aiogram import Router, F, types
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

@router.callback_query(F.data == "support_info")
async def support_info(c: types.CallbackQuery):
    # Используем HTML, чтобы нижнее подчеркивание в нике не ломало код
    text = (
        "<b>◈ СЛУЖБА ПОДДЕРЖКИ MI TEXNO 🛡</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Наши специалисты помогут Вам с выбором.\n\n"
        "Для связи с менеджером напишите:\n"
        "👉 @Mi_Texn0\n\n"
        "Мы всегда на связи!"
    )
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="to_main"))
    
    await c.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="HTML")
