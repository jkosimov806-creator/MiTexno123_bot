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
    waiting_for_name, waiting_for_phone, waiting_for_address = State(), State(), State()

class AdminState(StatesGroup):
    waiting_for_broadcast = State()
    add_item_name, add_item_price, add_item_desc, add_item_photo = State(), State(), State(), State()

# --- БАЗА ДАННЫХ (храним юзеров и товары) ---
def db_query(sql, params=(), fetch=False):
    with sqlite3.connect('mi_texno.db') as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        if fetch: return cursor.fetchall()
        conn.commit()

db_query('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)')
db_query('CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price TEXT, desc TEXT, photo TEXT)')

# Кнопки главного меню
def main_kb():
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="📦 Каталог товаров", callback_data="catalog_0"))
    kb.row(types.InlineKeyboardButton(text="🆘 Поддержка", url=SUPPORT_LINK))
    return kb.as_markup()

@dp.message(CommandStart())
async def start(message: types.Message):
    db_query('INSERT OR IGNORE INTO users VALUES (?)', (message.from_user.id,))
    await message.answer(f"**Вас приветствует Mi Texno** 📱\n\nБлагодарим за визит! Что Вы хотите сделать?", reply_markup=main_kb(), parse_mode="Markdown")

# --- КАТАЛОГ (АНКЕТЫ) ---
@dp.callback_query(F.data.startswith("catalog_"))
async def show_catalog(callback: types.CallbackQuery):
    items = db_query('SELECT * FROM items', fetch=True)
    if not items:
        return await callback.answer("Каталог пока пуст. Админ, добавь товары!", show_alert=True)
    
    idx = int(callback.data.split("_")[1])
    item = items[idx] # [id, name, price, desc, photo]
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="📥 Купить", callback_data=f"buy_{item[0]}"))
    
    # Листалка
    nav = []
    for i in range(len(items)):
        nav.append(types.InlineKeyboardButton(text=f"•{i+1}•" if i == idx else str(i+1), callback_data=f"catalog_{i}"))
    kb.row(*nav)
    kb.row(types.InlineKeyboardButton(text="⬅️ Меню", callback_data="to_menu"))

    await callback.message.delete()
    await callback.message.answer_photo(photo=item[4], caption=f"**{item[1]}**\n\n{item[3]}\n\n**Цена:** {item[2]}", reply_markup=kb.as_markup(), parse_mode="Markdown")

# --- ОФОРМЛЕНИЕ ЗАКАЗА ---
@dp.callback_query(F.data.startswith("buy_"))
async def buy(callback: types.CallbackQuery, state: FSMContext):
    kb = InlineKeyboardBuilder()
    for b in ["Alif Bank 🟢", "Eskhata Bank 🔴", "Dushanbe City 🟡"]:
        kb.row(types.InlineKeyboardButton(text=b, callback_data=f"pay_{b}"))
    await callback.message.answer("Выберите банк для оплаты:", reply_markup=kb.as_markup())
    await state.set_state(OrderState.waiting_for_name)

@dp.callback_query(F.data.startswith("pay_"))
async def set_bank(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(bank=callback.data.split("_")[1])
    await callback.message.answer("Введите Ваше Имя:")

@dp.message(OrderState.waiting_for_name)
async def name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text); await message.answer("Введите номер (+992XXXXXXXXX):")
    await state.set_state(OrderState.waiting_for_phone)

@dp.message(OrderState.waiting_for_phone)
async def phone(message: types.Message, state: FSMContext):
    if re.fullmatch(r"^\+992\d{9}$", message.text):
        await state.update_data(phone=message.text); await message.answer("Введите адрес доставки:")
        await state.set_state(OrderState.waiting_for_address)
    else: await message.answer("❌ Ошибка! Формат: +992 и 9 цифр.")

@dp.message(OrderState.waiting_for_address)
async def address(message: types.Message, state: FSMContext):
    d = await state.get_data()
    order = f"🆕 **ЗАКАЗ!**\nИмя: {d['name']}\nТел: {d['phone']}\nАдрес: {message.text}\nБанк: {d['bank']}"
    await bot.send_message(ADMIN_ID, order)
    await message.answer("✅ **Вы сделали заказ!** Ожидайте подтверждения.", reply_markup=main_kb())
    await state.clear()

# --- АДМИНКА ---
@dp.message(Command("admin"))
async def admin(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ Добавить товар", callback_data="add_item"))
    kb.row(types.InlineKeyboardButton(text="📢 Рассылка", callback_data="broadcast"))
    await message.answer("🛠 Панель Mi Texno", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "add_item")
async def add_start(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("Введите название товара:"); await state.set_state(AdminState.add_item_name)

@dp.message(AdminState.add_item_name)
async def add_n(m: types.Message, state: FSMContext):
    await state.update_data(n=m.text); await m.answer("Цена:"); await state.set_state(AdminState.add_item_price)

@dp.message(AdminState.add_item_price)
async def add_p(m: types.Message, state: FSMContext):
    await state.update_data(p=m.text); await m.answer("Описание:"); await state.set_state(AdminState.add_item_desc)

@dp.message(AdminState.add_item_desc)
async def add_d(m: types.Message, state: FSMContext):
    await state.update_data(d=m.text); await m.answer("Пришлите фото товара:"); await state.set_state(AdminState.add_item_photo)

@dp.message(AdminState.add_item_photo, F.photo)
async def add_ph(m: types.Message, state: FSMContext):
    data = await state.get_data()
    db_query('INSERT INTO items (name, price, desc, photo) VALUES (?,?,?,?)', (data['n'], data['p'], data['d'], m.photo[-1].file_id))
    await m.answer("✅ Товар успешно добавлен в каталог!"); await state.clear()

@dp.callback_query(F.data == "to_menu")
async def m_back(c: types.CallbackQuery):
    await c.message.delete(); await start(c.message)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
