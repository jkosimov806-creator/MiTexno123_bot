import asyncio, re, sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import TOKEN, ADMIN_ID, SUPPORT_LINK

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- СОСТОЯНИЯ ---
class OrderState(StatesGroup):
    waiting_for_count = State()
    waiting_for_promo = State()
    waiting_for_name, waiting_for_phone, waiting_for_address = State(), State(), State()
    waiting_for_check = State()

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

with sqlite3.connect('mi_texno.db') as conn:
    conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)')
    conn.execute('CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price INTEGER, desc TEXT, photo TEXT)')
    conn.execute('CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, discount INTEGER)')

# --- КЛАВИАТУРЫ ---
def main_kb(user_id):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="📦 Каталог товаров", callback_data="catalog_0"))
    kb.row(types.InlineKeyboardButton(text="🛒 Моя корзина", callback_data="view_cart"))
    kb.row(types.InlineKeyboardButton(text="🆘 Поддержка", url=SUPPORT_LINK))
    if user_id == ADMIN_ID:
        kb.row(types.InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_menu"))
    return kb.as_markup()

@dp.message(CommandStart())
async def start(message: types.Message):
    db_query('INSERT OR IGNORE INTO users VALUES (?)', (message.from_user.id,))
    await message.answer(
        "**Благодарим за выбор Mi Texno!** 📱\n\nМы подготовили для Вас лучшие технологичные решения.\nЧто Вы хотите сделать в первую очередь?",
        reply_markup=main_kb(message.from_user.id), parse_mode="Markdown"
    )

# --- КАТАЛОГ С ЖИВЫМИ КНОПКАМИ +/- ---
@dp.callback_query(F.data.startswith("catalog_"))
async def show_catalog(c: types.CallbackQuery):
    items = db_query('SELECT * FROM items', fetch=True)
    if not items: return await c.answer("Каталог временно пуст.", show_alert=True)
    idx = int(c.data.split("_")[-1]); item = items[idx]
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ Добавить в корзину", callback_data=f"start_count_{item[0]}"))
    nav = [types.InlineKeyboardButton(text=f"•{i+1}•" if i == idx else str(i+1), callback_data=f"catalog_{i}") for i in range(len(items))]
    kb.row(*nav)
    kb.row(types.InlineKeyboardButton(text="⬅️ В меню", callback_data="to_main"))
    await c.message.delete()
    await c.message.answer_photo(photo=item[4], caption=f"**{item[1]}**\n\n{item[3]}\n\n**Цена:** {item[2]} сомони", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("start_count_"))
async def start_count(c: types.CallbackQuery, state: FSMContext):
    item_id = int(c.data.split("_")[-1])
    await state.update_data(cur_id=item_id, cur_qty=1)
    await update_count_msg(c.message, 1)

async def update_count_msg(msg, qty):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➖", callback_data="cnt_minus"),
           types.InlineKeyboardButton(text=f"шт: {qty}", callback_data="none"),
           types.InlineKeyboardButton(text="➕", callback_data="cnt_plus"))
    kb.row(types.InlineKeyboardButton(text="✅ Подтвердить", callback_data="cnt_done"))
    await msg.edit_reply_markup(reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("cnt_"))
async def handle_cnt(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data(); qty = data.get('cur_qty', 1)
    if c.data == "cnt_plus": qty += 1
    elif c.data == "cnt_minus" and qty > 1: qty -= 1
    elif c.data == "cnt_done":
        cart = data.get('cart', {})
        cart[data['cur_id']] = cart.get(data['cur_id'], 0) + qty
        await state.update_data(cart=cart); await c.answer("Добавлено в корзину!"); return await show_catalog(c)
    await state.update_data(cur_qty=qty); await update_count_msg(c.message, qty)

# --- КОРЗИНА И ПРОМОКОДЫ ---
@dp.callback_query(F.data == "view_cart")
async def view_cart(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data(); cart = data.get('cart', {}); promo = data.get('promo_discount', 0)
    if not cart: return await c.answer("Ваша корзина пуста.", show_alert=True)
    
    res = "**🛒 Ваша корзина:**\n\n"; total = 0
    for i_id, q in cart.items():
        i = db_query('SELECT name, price FROM items WHERE id = ?', (i_id,), fetch_one=True)
        sum_i = int(i[1]) * q; total += sum_i
        res += f"• {i[0]} — {q} шт. ({sum_i} сом.)\n"
    
    final_total = max(0, total - promo)
    res += f"\n**Итого:** {total} сом."
    if promo: res += f"\n**Скидка по промокоду:** -{promo} сом.\n**К оплате:** {final_total} сом."
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🎟 Ввести промокод", callback_data="apply_promo"))
    kb.row(types.InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout"))
    kb.row(types.InlineKeyboardButton(text="🗑 Очистить", callback_data="clear_cart"))
    await c.message.answer(res, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "apply_promo")
async def promo_start(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("Введите Ваш промокод:"); await state.set_state(OrderState.waiting_for_promo)

@dp.message(OrderState.waiting_for_promo)
async def promo_check(m: types.Message, state: FSMContext):
    promo = db_query('SELECT discount FROM promos WHERE code = ?', (m.text,), fetch_one=True)
    if promo:
        await state.update_data(promo_discount=promo[0], promo_code=m.text)
        await m.answer(f"✅ Промокод активирован! Скидка {promo[0]} сомони.")
    else: await m.answer("❌ Промокод не найден или уже использован.")
    await view_cart(m, state)

# --- ОФОРМЛЕНИЕ (ОПЛАТА ПОСЛЕ АДРЕСА) ---
@dp.callback_query(F.data == "checkout")
async def checkout(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("Введите Ваше Имя:"); await state.set_state(OrderState.waiting_for_name)

@dp.message(OrderState.waiting_for_name)
async def ch_n(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text); await m.answer("Номер телефона (+992XXXXXXXXX):"); await state.set_state(OrderState.waiting_for_phone)

@dp.message(OrderState.waiting_for_phone)
async def ch_p(m: types.Message, state: FSMContext):
    if re.fullmatch(r"^\+992\d{9}$", m.text):
        await state.update_data(phone=m.text); await m.answer("Адрес доставки:"); await state.set_state(OrderState.waiting_for_address)
    else: await m.answer("❌ Ошибка! Формат: +992 и 9 цифр.")

@dp.message(OrderState.waiting_for_address)
async def ch_a(m: types.Message, state: FSMContext):
    await state.update_data(addr=m.text)
    kb = InlineKeyboardBuilder()
    for b in ["Alif 🟢", "Eskhata 🔴", "DC 🟡"]: kb.row(types.InlineKeyboardButton(text=b, callback_data=f"pay_{b}"))
    await m.answer("Выберите банк для оплаты:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("pay_"))
async def ch_bank(c: types.CallbackQuery, state: FSMContext):
    await state.update_data(bank=c.data.split("_")[-1])
    await c.message.answer("Реквизиты: `+992928663510`\nПожалуйста, пришлите скриншот чека."); await state.set_state(OrderState.waiting_for_check)

@dp.message(OrderState.waiting_for_check, F.photo)
async def ch_final(m: types.Message, state: FSMContext):
    d = await state.get_data(); cart_text = ""; total = 0
    for i_id, q in d['cart'].items():
        i = db_query('SELECT name, price FROM items WHERE id = ?', (i_id,), fetch_one=True)
        cart_text += f"- {i[0]} x{q}\n"; total += int(i[1]) * q
    
    final_sum = max(0, total - d.get('promo_discount', 0))
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"adm_ok_{m.from_user.id}_{d.get('promo_code','none')}"))
    kb.row(types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_no_{m.from_user.id}"))
    
    msg = f"🆕 **ЗАКАЗ!**\n{cart_text}\n💰 Сумма: {final_sum} сом.\n👤 {d['name']}\n📞 {d['phone']}\n🏠 {d['addr']}\n💳 {d['bank']}"
    await bot.send_photo(ADMIN_ID, photo=m.photo[-1].file_id, caption=msg, reply_markup=kb.as_markup())
    await m.answer("✅ **Заказ отправлен!** Менеджер свяжется с Вами."); await state.clear()

# --- АДМИНКА ---
@dp.callback_query(F.data == "admin_menu")
async def ad_menu(c: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ Товар", callback_data="add_item"), types.InlineKeyboardButton(text="🎟 Промокод", callback_data="add_promo"))
    kb.row(types.InlineKeyboardButton(text="📢 Рассылка", callback_data="broadcast"))
    await c.message.answer("🛠 Админ-панель", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("adm_"))
async def ad_dec(c: types.CallbackQuery):
    _, res, uid, p_code = c.data.split("_")
    if res == "ok":
        await bot.send_message(uid, "🔔 **Заказ подтвержден!** Готовим к отправке.")
        if p_code != "none": db_query('DELETE FROM promos WHERE code = ?', (p_code,))
    else: await bot.send_message(uid, "❌ **Заказ отклонен.**")
    await c.message.edit_caption(caption=c.message.caption + f"\n\nСтатус: {res.upper()}")

@dp.callback_query(F.data == "add_promo")
async def ad_p1(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("Введите код (напр. Summer50):"); await state.set_state(AdminState.add_promo_code)

@dp.message(AdminState.add_promo_code)
async def ad_p2(m: types.Message, state: FSMContext):
    await state.update_data(pc=m.text); await m.answer("Сумма скидки (сом):"); await state.set_state(AdminState.add_promo_discount)

@dp.message(AdminState.add_promo_discount)
async def ad_p3(m: types.Message, state: FSMContext):
    d = await state.get_data(); db_query('INSERT INTO promos VALUES (?,?)', (d['pc'], int(m.text)))
    await m.answer(f"✅ Промокод {d['pc']} на {m.text} сом. создан!"); await state.clear()

# [Сюда вставь функции add_item_name... и broadcast из старого кода]

async def main():
    await bot.delete_webhook(drop_pending_updates=True); await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
