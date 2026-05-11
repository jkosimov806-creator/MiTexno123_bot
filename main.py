import asyncio, re, sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import TOKEN, ADMIN_ID, SUPPORT_LINK

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Состояния
class OrderState(StatesGroup):
    waiting_for_name, waiting_for_phone, waiting_for_address = State(), State(), State()

class AdminState(StatesGroup):
    waiting_for_broadcast = State()
    add_item_name, add_item_price, add_item_desc, add_item_photo = State(), State(), State(), State()

# --- РАБОТА С БАЗОЙ ---
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

# --- ЛОГИКА ---
@dp.message(CommandStart())
async def start(message: types.Message):
    db_query('INSERT OR IGNORE INTO users VALUES (?)', (message.from_user.id,))
    await message.answer(
        "**Вас приветствует Mi Texno** 📱\n\nБлагодарим за визит! Что Вы хотите сделать?",
        reply_markup=main_kb(message.from_user.id), parse_mode="Markdown"
    )

@dp.callback_query(F.data == "admin_menu")
async def admin_menu_call(c: types.CallbackQuery):
    if c.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ Добавить товар", callback_data="add_item"))
    kb.row(types.InlineKeyboardButton(text="📢 Рассылка", callback_data="broadcast"))
    await c.message.answer("🛠 **Панель управления Mi Texno**", reply_markup=kb.as_markup())

# Каталог
@dp.callback_query(F.data.startswith("catalog_"))
async def show_catalog(callback: types.CallbackQuery):
    items = db_query('SELECT * FROM items', fetch=True)
    if not items:
        return await callback.answer("Каталог пока пуст!", show_alert=True)
    
    idx = int(callback.data.split("_")[1])
    if idx >= len(items): idx = 0
    item = items[idx]
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="📥 Купить", callback_data=f"buy_{item[0]}"))
    
    nav = []
    for i in range(len(items)):
        nav.append(types.InlineKeyboardButton(text=f"•{i+1}•" if i == idx else str(i+1), callback_data=f"catalog_{i}"))
    kb.row(*nav)
    kb.row(types.InlineKeyboardButton(text="⬅️ Меню", callback_data="to_main"))

    caption = f"**{item[1]}**\n\n{item[3] if item[3] else ''}\n\n**Цена:** {item[2]}"
    await callback.message.delete()
    await callback.message.answer_photo(photo=item[4], caption=caption, reply_markup=kb.as_markup(), parse_mode="Markdown")

# Заказ
@dp.callback_query(F.data.startswith("buy_"))
async def buy_process(c: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    for b in ["Alif Bank 🟢", "Eskhata Bank 🔴", "Dushanbe City 🟡"]:
        kb.row(types.InlineKeyboardButton(text=b, callback_data=f"pay_{b}"))
    await c.message.answer("Выберите банк для оплаты:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("pay_"))
async def pay_set(c: types.CallbackQuery, state: FSMContext):
    await state.update_data(bank=c.data.split("_")[1])
    await c.message.answer("Введите Ваше Имя:")
    await state.set_state(OrderState.waiting_for_name)

@dp.message(OrderState.waiting_for_name)
async def get_n(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text); await m.answer("Введите номер (+992XXXXXXXXX):")
    await state.set_state(OrderState.waiting_for_phone)

@dp.message(OrderState.waiting_for_phone)
async def get_p(m: types.Message, state: FSMContext):
    if re.fullmatch(r"^\+992\d{9}$", m.text):
        await state.update_data(phone=m.text); await m.answer("Введите адрес:")
        await state.set_state(OrderState.waiting_for_address)
    else: await m.answer("❌ Формат: +992 и 9 цифр.")

@dp.message(OrderState.waiting_for_address)
async def get_a(m: types.Message, state: FSMContext):
    d = await state.get_data()
    order = f"🆕 **ЗАКАЗ!**\nИмя: {d['name']}\nТел: {d['phone']}\nАдрес: {m.text}\nБанк: {d['bank']}"
    await bot.send_message(ADMIN_ID, order)
    await m.answer("✅ **Заказ сделан!** Ожидайте.", reply_markup=main_kb(m.from_user.id))
    await state.clear()

# Рассылка
@dp.callback_query(F.data == "broadcast")
async def br_st(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("Введите текст рассылки:"); await state.set_state(AdminState.waiting_for_broadcast)

@dp.message(AdminState.waiting_for_broadcast)
async def br_do(m: types.Message, state: FSMContext):
    users = db_query('SELECT id FROM users', fetch=True)
    count = 0
    for u in users:
        try: await bot.send_message(u[0], m.text); count += 1
        except: pass
    await m.answer(f"✅ Отправлено: {count} чел."); await state.clear()

# Добавление товара
@dp.callback_query(F.data == "add_item")
async def add_i(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("Название товара:"); await state.set_state(AdminState.add_item_name)

@dp.message(AdminState.add_item_name)
async def add_i_n(m: types.Message, state: FSMContext):
    await state.update_data(n=m.text); await m.answer("Цена:"); await state.set_state(AdminState.add_item_price)

@dp.message(AdminState.add_item_price)
async def add_i_p(m: types.Message, state: FSMContext):
    await state.update_data(p=m.text); await m.answer("Описание (или /skip):"); await state.set_state(AdminState.add_item_desc)

@dp.message(AdminState.add_item_desc)
async def add_i_d(m: types.Message, state: FSMContext):
    d = "" if m.text == "/skip" else m.text
    await state.update_data(d=d); await m.answer("Пришлите фото:"); await state.set_state(AdminState.add_item_photo)

@dp.message(AdminState.add_item_photo, F.photo)
async def add_i_ph(m: types.Message, state: FSMContext):
    data = await state.get_data()
    db_query('INSERT INTO items (name, price, desc, photo) VALUES (?,?,?,?)', (data['n'], data['p'], data['d'], m.photo[-1].file_id))
    await m.answer("✅ Готово!", reply_markup=main_kb(m.from_user.id)); await state.clear()

@dp.callback_query(F.data == "to_main")
async def back_m(c: types.CallbackQuery):
    await c.message.delete(); await start(c.message)

async def main():
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
