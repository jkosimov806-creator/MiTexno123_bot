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
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_bank = State()
    waiting_for_check = State()

class AdminState(StatesGroup):
    waiting_for_broadcast = State()
    add_item_name = State()
    add_item_price = State()
    add_item_desc = State()
    add_item_photo = State()

# --- БАЗА ---
def init_db():
    with sqlite3.connect('mi_texno.db') as conn:
        cursor = conn.cursor()
        cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)')
        cursor.execute('CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price TEXT, desc TEXT, photo TEXT)')
        conn.commit()

def db_query(sql, params=(), fetch=False, fetch_one=False):
    with sqlite3.connect('mi_texno.db') as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        if fetch_one: return cursor.fetchone()
        if fetch: return cursor.fetchall()
        conn.commit()

# --- КНОПКИ ---
def main_kb(user_id):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="📦 Каталог товаров", callback_data="catalog_0"))
    kb.row(types.InlineKeyboardButton(text="🆘 Поддержка", url=SUPPORT_LINK))
    if user_id == ADMIN_ID:
        kb.row(types.InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_menu"))
    return kb.as_markup()

@dp.message(CommandStart())
async def start(message: types.Message):
    db_query('INSERT OR IGNORE INTO users VALUES (?)', (message.from_user.id,))
    await message.answer(f"**Вас приветствует Mi Texno** 📱\n\nЧто Вы хотите сделать?", reply_markup=main_kb(message.from_user.id), parse_mode="Markdown")

# --- КАТАЛОГ ---
@dp.callback_query(F.data.startswith("catalog_"))
async def show_catalog(c: types.CallbackQuery):
    items = db_query('SELECT * FROM items', fetch=True)
    if not items: return await c.answer("Каталог пуст!", show_alert=True)
    idx = int(c.data.split("_")[1]); item = items[idx]
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="📥 Купить", callback_data=f"buy_{item[0]}"))
    nav = [types.InlineKeyboardButton(text=f"•{i+1}•" if i == idx else str(i+1), callback_data=f"catalog_{i}") for i in range(len(items))]
    kb.row(*nav)
    kb.row(types.InlineKeyboardButton(text="⬅️ Меню", callback_data="to_main"))
    await c.message.delete()
    await c.message.answer_photo(photo=item[4], caption=f"**{item[1]}**\n\n{item[3]}\n\n**Цена:** {item[2]}", reply_markup=kb.as_markup(), parse_mode="Markdown")

# --- ОФОРМЛЕНИЕ ЗАКАЗА (НОВЫЙ ПОРЯДОК) ---
@dp.callback_query(F.data.startswith("buy_"))
async def order_start(c: types.CallbackQuery, state: FSMContext):
    item_id = c.data.split("_")[1]
    item = db_query('SELECT name FROM items WHERE id = ?', (item_id,), fetch_one=True)
    await state.update_data(product=item[0])
    await c.message.answer("Введите Ваше Имя:")
    await state.set_state(OrderState.waiting_for_name)

@dp.message(OrderState.waiting_for_name)
async def order_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text); await m.answer("Введите номер (+992XXXXXXXXX):")
    await state.set_state(OrderState.waiting_for_phone)

@dp.message(OrderState.waiting_for_phone)
async def order_phone(m: types.Message, state: FSMContext):
    if re.fullmatch(r"^\+992\d{9}$", m.text):
        await state.update_data(phone=m.text); await m.answer("Введите адрес доставки:")
        await state.set_state(OrderState.waiting_for_address)
    else: await m.answer("❌ Формат: +992 и 9 цифр.")

@dp.message(OrderState.waiting_for_address)
async def order_address(m: types.Message, state: FSMContext):
    await state.update_data(address=m.text)
    kb = InlineKeyboardBuilder()
    for b in ["Alif Bank 🟢", "Eskhata Bank 🔴", "Dushanbe City 🟡"]:
        kb.row(types.InlineKeyboardButton(text=b, callback_data=f"pay_{b}"))
    await m.answer("Выберите банк для оплаты:", reply_markup=kb.as_markup())
    await state.set_state(OrderState.waiting_for_bank)

@dp.callback_query(OrderState.waiting_for_bank)
async def order_bank(c: types.CallbackQuery, state: FSMContext):
    bank = c.data.split("_")[1]
    await state.update_data(bank=bank)
    await c.message.answer(f"Пожалуйста, переведите оплату по номеру: `+992928663510` ({bank})\n\nПосле оплаты **пришлите скриншот чека** в этот чат.", parse_mode="Markdown")
    await state.set_state(OrderState.waiting_for_check)

@dp.message(OrderState.waiting_for_check, F.photo)
async def order_check(m: types.Message, state: FSMContext):
    d = await state.get_data()
    # Отправляем админу сообщение с кнопками
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"adm_ok_{m.from_user.id}"))
    kb.row(types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_no_{m.from_user.id}"))
    
    admin_msg = f"🆕 **НОВЫЙ ЗАКАЗ!**\n\n📦 Товар: {d['product']}\n👤 Имя: {d['name']}\n📞 Тел: {d['phone']}\n🏠 Адрес: {d['address']}\n💳 Банк: {d['bank']}"
    await bot.send_photo(ADMIN_ID, photo=m.photo[-1].file_id, caption=admin_msg, reply_markup=kb.as_markup())
    
    await m.answer("✅ **Чек получен!** Ваш заказ отправлен на проверку администратору. Ожидайте уведомления.")
    await state.clear()

# --- ЛОГИКА АДМИНА (ПОДТВЕРЖДЕНИЕ) ---
@dp.callback_query(F.data.startswith("adm_"))
async def admin_decision(c: types.CallbackQuery):
    action, user_id = c.data.split("_")[1], c.data.split("_")[2]
    if action == "ok":
        await bot.send_message(user_id, "🔔 **Ваш заказ подтвержден!** Наш курьер свяжется с Вами в ближайшее время.")
        await c.message.edit_caption(caption=c.message.caption + "\n\n✅ **ПОДТВЕРЖДЕНО**")
    else:
        await bot.send_message(user_id, "❌ **Ваш заказ отклонен.** Если у Вас есть вопросы, обратитесь в поддержку.")
        await c.message.edit_caption(caption=c.message.caption + "\n\n❌ **ОТКЛОНЕНО**")

# --- ОСТАЛЬНАЯ АДМИНКА ---
@dp.callback_query(F.data == "admin_menu")
async def admin_menu(c: types.CallbackQuery):
    if c.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ Добавить товар", callback_data="add_item"))
    kb.row(types.InlineKeyboardButton(text="📢 Рассылка", callback_data="broadcast"))
    await c.message.answer("🛠 Панель управления", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "broadcast")
async def br_st(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("Текст рассылки:"); await state.set_state(AdminState.waiting_for_broadcast)

@dp.message(AdminState.waiting_for_broadcast)
async def br_do(m: types.Message, state: FSMContext):
    users = db_query('SELECT id FROM users', fetch=True)
    count = 0
    for u in users:
        try: await bot.send_message(u[0], m.text); count += 1
        except: pass
    await m.answer(f"✅ Отправлено: {count}"); await state.clear()

@dp.callback_query(F.data == "add_item")
async def add_st(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("Название:"); await state.set_state(AdminState.add_item_name)

@dp.message(AdminState.add_item_name)
async def add_n(m: types.Message, state: FSMContext):
    await state.update_data(n=m.text); await m.answer("Цена:"); await state.set_state(AdminState.add_item_price)

@dp.message(AdminState.add_item_price)
async def add_p(m: types.Message, state: FSMContext):
    await state.update_data(p=m.text); await m.answer("Описание (/skip):"); await state.set_state(AdminState.add_item_desc)

@dp.message(AdminState.add_item_desc)
async def add_d(m: types.Message, state: FSMContext):
    d = "" if m.text == "/skip" else m.text
    await state.update_data(d=d); await m.answer("Фото:"); await state.set_state(AdminState.add_item_photo)

@dp.message(AdminState.add_item_photo, F.photo)
async def add_ph(m: types.Message, state: FSMContext):
    d = await state.get_data()
    db_query('INSERT INTO items (name, price, desc, photo) VALUES (?,?,?,?)', (d['n'], d['p'], d['d'], m.photo[-1].file_id))
    await m.answer("✅ Товар добавлен!"); await state.clear()

@dp.callback_query(F.data == "to_main")
async def back(c: types.CallbackQuery):
    await c.message.delete(); await start(c.message)

async def main():
    init_db(); await bot.delete_webhook(drop_pending_updates=True); await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
