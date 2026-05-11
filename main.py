import asyncio, re, sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import TOKEN, ADMIN_ID, SUPPORT_LINK

bot = Bot(token=TOKEN)
dp = Dispatcher()

class OrderState(StatesGroup):
    waiting_for_count = State()
    waiting_for_promo = State()
    waiting_for_name, waiting_for_phone, waiting_for_address = State(), State(), State()
    waiting_for_bank, waiting_for_check = State(), State()

class AdminState(StatesGroup):
    broadcast = State()
    add_item_name, add_item_price, add_item_desc, add_item_photo = State(), State(), State(), State()
    add_promo_code, add_promo_discount = State(), State()

# --- БАЗА ДАННЫХ ---
def db_query(sql, params=(), fetch=False, fetch_one=False):
    with sqlite3.connect('mi_texno.db') as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        if fetch_one: return cursor.fetchone()
        if fetch: return cursor.fetchall()
        conn.commit()

# --- КЛАВИАТУРЫ ---
def main_kb(user_id):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="▻ ПЕРЕЙТИ В КАТАЛОГ", callback_data="catalog_0"))
    kb.row(types.InlineKeyboardButton(text="🛒 МОЯ КОРЗИНА", callback_data="view_cart"))
    kb.row(types.InlineKeyboardButton(text="🛡 СЛУЖБА ПОДДЕРЖКИ", callback_data="support_info"))
    if user_id == ADMIN_ID:
        kb.row(types.InlineKeyboardButton(text="⚙️ АДМИН-ПАНЕЛЬ", callback_data="admin_menu"))
    return kb.as_markup()

@dp.message(CommandStart())
async def start(message: types.Message):
    db_query('INSERT OR IGNORE INTO users VALUES (?)', (message.from_user.id,))
    await message.answer(
        f"◈ **MI TEXNO | Premium Store** 📱\n━━━━━━━━━━━━━━━━━━━━\nЗдравствуйте! Рады видеть Вас. Используйте меню для навигации:",
        reply_markup=main_kb(message.from_user.id), parse_mode="Markdown"
    )

# --- ПОДДЕРЖКА (ТОЛЬКО ТВОЙ ТЕКСТ) ---
@dp.callback_query(F.data == "support_info")
async def support_call(c: types.CallbackQuery):
    text = (
        "◈ **СЛУЖБА ПОДДЕРЖКИ MI TEXNO** 🛡\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Наш менеджер всегда готов помочь Вам с выбором или оформлением заказа.\n\n"
        "Для связи напишите по адресу:\n"
        "👉 @Mi_Texn0\n\n"
        "Мы работаем для Вашего комфорта."
    )
    kb = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="⬅️ НАЗАД", callback_data="to_main"))
    await c.message.edit_text(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

# --- КАТАЛОГ ---
@dp.callback_query(F.data.startswith("catalog_"))
async def show_catalog(c: types.CallbackQuery):
    items = db_query('SELECT * FROM items', fetch=True)
    if not items: return await c.answer("Каталог временно пуст.", show_alert=True)
    idx = int(c.data.split("_")[-1]) % len(items); item = items[idx]
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ ДОБАВИТЬ В КОРЗИНУ", callback_data=f"start_count_{item[0]}"))
    nav = [types.InlineKeyboardButton(text=f"• {i+1} •" if i == idx else str(i+1), callback_data=f"catalog_{i}") for i in range(len(items))]
    kb.row(*nav)
    kb.row(types.InlineKeyboardButton(text="⬅️ В МЕНЮ", callback_data="to_main"))
    caption = f"┃ **{item[1]}**\n┃ ━━━━━━━━━━━━━━\n┃ {item[3] if item[3] else '—'}\n\n┃ ◈ **Цена:** {item[2]} TJS"
    await c.message.delete()
    await c.message.answer_photo(photo=item[4], caption=caption, reply_markup=kb.as_markup(), parse_mode="Markdown")

# --- СЧЕТЧИК +/- ---
@dp.callback_query(F.data.startswith("start_count_"))
async def start_count(c: types.CallbackQuery, state: FSMContext):
    item_id = int(c.data.split("_")[-1])
    await state.update_data(cur_id=item_id, cur_qty=1)
    await update_count_msg(c, 1)

async def update_count_msg(c, qty):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="−", callback_data="cnt_minus"),
           types.InlineKeyboardButton(text=f"{qty} шт.", callback_data="none"),
           types.InlineKeyboardButton(text="+", callback_data="cnt_plus"))
    kb.row(types.InlineKeyboardButton(text="✅ ПОДТВЕРДИТЬ", callback_data="cnt_done"))
    await c.message.edit_reply_markup(reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("cnt_"))
async def handle_cnt(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data(); qty = data.get('cur_qty', 1)
    if c.data == "cnt_plus": qty += 1
    elif c.data == "cnt_minus" and qty > 1: qty -= 1
    elif c.data == "cnt_done":
        cart = data.get('cart', {})
        cart[str(data['cur_id'])] = cart.get(str(data['cur_id']), 0) + qty
        await state.update_data(cart=cart)
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="📦 К ДРУГИМ ТОВАРАМ", callback_data="catalog_0"))
        kb.row(types.InlineKeyboardButton(text="🛒 В КОРЗИНУ", callback_data="view_cart"))
        return await c.message.answer("✅ Товар добавлен в корзину!", reply_markup=kb.as_markup())
    await state.update_data(cur_qty=qty); await update_count_msg(c, qty)

# --- КОРЗИНА И ПРОМО ---
@dp.callback_query(F.data == "view_cart")
async def view_cart(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data(); cart = data.get('cart', {}); promo = data.get('promo_discount', 0)
    if not cart: return await c.answer("Ваша корзина пуста.", show_alert=True)
    res = "◈ **ВАША КОРЗИНА**\n━━━━━━━━━━━━━━\n"; total = 0
    for i_id, q in cart.items():
        i = db_query('SELECT name, price FROM items WHERE id = ?', (i_id,), fetch_one=True)
        if i:
            sum_i = i[1] * q; total += sum_i
            res += f"▻ {i[0]} | {q} шт. — `{sum_i} TJS`\n"
    final_total = max(0, total - promo)
    res += f"━━━━━━━━━━━━━━\n**Итого:** {total} TJS\n"
    if promo: res += f"**Промокод:** -{promo} TJS\n**К оплате:** `{final_total} TJS`"
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🎟 ПРОМОКОД", callback_data="apply_promo"), types.InlineKeyboardButton(text="💳 ОФОРМИТЬ", callback_data="checkout"))
    kb.row(types.InlineKeyboardButton(text="🗑 ОЧИСТИТЬ", callback_data="clear_cart"), types.InlineKeyboardButton(text="⬅️ МЕНЮ", callback_data="to_main"))
    await c.message.answer(res, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "apply_promo")
async def apply_promo_call(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("Введите промокод:"); await state.set_state(OrderState.waiting_for_promo)

@dp.message(OrderState.waiting_for_promo)
async def check_promo_msg(m: types.Message, state: FSMContext):
    promo = db_query('SELECT discount FROM promos WHERE code = ?', (m.text,), fetch_one=True)
    if promo:
        await state.update_data(promo_discount=promo[0], promo_code=m.text)
        await m.answer(f"✅ Активировано! Скидка {promo[0]} TJS.")
    else: await m.answer("❌ Промокод не найден."); await state.set_state(None); await view_cart(m, state)

# --- АДМИНКА ---
@dp.callback_query(F.data == "admin_menu")
async def ad_menu_call(c: types.CallbackQuery):
    if c.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ ТОВАР", callback_data="add_item"), types.InlineKeyboardButton(text="🎟 ПРОМО", callback_data="add_promo"))
    kb.row(types.InlineKeyboardButton(text="📢 РАССЫЛКА", callback_data="broadcast"))
    await c.message.answer("🛠 АДМИН-ПАНЕЛЬ MI TEXNO", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "broadcast")
async def ad_br_st(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("Текст рассылки:"); await state.set_state(AdminState.broadcast)

@dp.message(AdminState.broadcast)
async def ad_br_do(m: types.Message, state: FSMContext):
    users = db_query('SELECT id FROM users', fetch=True); count = 0
    for u in users:
        try: await bot.send_message(u[0], m.text); count += 1
        except: pass
    await m.answer(f"✅ Рассылка завершена ({count} чел.)"); await state.clear()

@dp.callback_query(F.data == "add_item")
async def ad_add_st(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("Название товара:"); await state.set_state(AdminState.add_item_name)

@dp.message(AdminState.add_item_name)
async def ad_add_n(m: types.Message, state: FSMContext):
    await state.update_data(n=m.text); await m.answer("Цена:"); await state.set_state(AdminState.add_item_price)

@dp.message(AdminState.add_item_price)
async def ad_add_p(m: types.Message, state: FSMContext):
    await state.update_data(p=m.text); await m.answer("Описание (/skip):"); await state.set_state(AdminState.add_item_desc)

@dp.message(AdminState.add_item_desc)
async def ad_add_d(m: types.Message, state: FSMContext):
    d = "" if m.text == "/skip" else m.text
    await state.update_data(d=d); await m.answer("Пришлите фото:"); await state.set_state(AdminState.add_item_photo)

@dp.message(AdminState.add_item_photo, F.photo)
async def ad_add_ph(m: types.Message, state: FSMContext):
    d = await state.get_data()
    db_query('INSERT INTO items (name, price, desc, photo) VALUES (?,?,?,?)', (d['n'], int(d['p']), d['d'], m.photo[-1].file_id))
    await m.answer("✅ Товар успешно добавлен!"); await state.clear()

@dp.callback_query(F.data == "to_main")
async def back_to_main(c: types.CallbackQuery):
    try: await c.message.delete()
    except: pass
    await start(c.message)

async def main():
    with sqlite3.connect('mi_texno.db') as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)')
        conn.execute('CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price INTEGER, desc TEXT, photo TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, discount INTEGER)')
    await bot.delete_webhook(drop_pending_updates=True); await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
