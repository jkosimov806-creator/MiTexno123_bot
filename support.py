from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

@router.callback_query(F.data == "support_info")
async def support_handler(c: types.CallbackQuery):
    text = (
        "◈ **СЛУЖБА ПОДДЕРЖКИ MI TEXNO** 🛡\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Наши специалисты всегда готовы помочь Вам с выбором или оформлением заказа.\n\n"
        "Для связи с менеджером напишите по адресу:\n"
        "👉 @Mi_Texn0\n\n"
        "Мы работаем для Вашего комфорта."
    )
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="⬅️ ВЕРНУТЬСЯ В МЕНЮ", callback_data="to_main"))
    
    # Пытаемся отредактировать текст, если не выйдет — шлем новое
    try:
        await c.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
    except:
        await c.message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")
        await c.message.delete()
