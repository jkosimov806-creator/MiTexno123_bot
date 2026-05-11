from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from database import db_query

router = Router()

@router.callback_query(F.data.startswith("catalog_"))
async def show_cat(c: types.CallbackQuery):
    items = db_query('SELECT * FROM items', fetch=True)
    if not items: return await c.answer("Каталог временно пуст.", show_alert=True)
    
    idx = int(c.data.split("_")[-1]) % len(items)
    item = items[idx] # [id, name, price, desc, photo, categorie]
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ В КОРЗИНУ", callback_data=f"buy_{item[0]}"))
    nav = [types.InlineKeyboardButton(text=f"•{i+1}•" if i == idx else str(i+1), callback_data=f"catalog_{i}") for i in range(len(items))]
    kb.row(*nav)
    kb.row(types.InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="to_main"))
    
    caption = (
        f"<b>{item[1]}</b>\n"
        f"🏷 Категория: {item[5]}\n"
        f"━━━━━━━━━━━━━━\n"
        f"{item[3] if item[3] else '—'}\n\n"
        f"<b>Цена:</b> {item[2]} TJS"
    )
    await c.message.delete()
    await c.message.answer_photo(photo=item[4], caption=caption, reply_markup=kb.as_markup(), parse_mode="HTML")
