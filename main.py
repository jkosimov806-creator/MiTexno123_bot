import asyncio
import re
import sqlite3
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
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()

class AdminState(StatesGroup):
    waiting_for_broadcast_text = State()

# Работа с базой данных для рассылки
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users')
    users = cursor.fetchall()
    conn.close()
    return [user[0] for user in users]

PRODUCTS = [
    {"id": 0, "name": "Xiaomi 14 Ultra", "price": "14500 c.", "desc": "Камера Leica.", "img": "https://media-amazon.com"},
    {"id": 1, "name": "iPhone 15 Pro Max", "price": "13200 c.", "desc": "Титан.", "img": "https://clck.ru"},
    {"id": 2, "name": "AirPods Pro 2", "price": "2950 c.", "desc": "Звук топ.", "img": "https://clck.ru"}
]

# Кнопки
def main_kb():
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="📦 Каталог", callback_data="cat_0"))
    kb.row(types.InlineKeyboardButton(text="🆘 Поддержка", url=SUPPORT_LINK))
    return kb.as_markup()

# --- КЛИЕНТСКАЯ ЧАСТЬ ---

@dp.message(CommandStart())
async def start(message: types.Message):
    add_user(message.from_user.id) # Запоминаем юзера для рассылки
    await message.answer(
        "**Вас приветствует Mi Texno** 📱\n\nБлагодарим за визит! Что Вы хотите сделать?",
        reply_markup=main_kb(), parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("cat_"))
async def show_item(callback: types.CallbackQuery):
    index = int(callback.data.split("_")[1])
    p = PRODUCTS[index]
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="📥 Купить", callback_data=f"buy_{index}"))
    nav_btns = [types.InlineKeyboardButton(text=f"• {i+1} •" if i == index else str(i+1), callback_data=f"cat_{i}") for i in range(len(PRODUCTS))]
    kb.row(*nav_btns)
    kb.row(types.InlineKeyboardButton(text="⬅️ В меню", callback_data="to_main"))
    
    try:
        await callback.message.edit_media(
            media=types.InputMediaPhoto(media=p['img'], caption=f"**{p['name']}**\n{p['price']}\n{p['desc']}", parse_mode="Markdown"),
            reply_markup=kb.as_markup()
        )
    except:
        await callback.message.answer_photo(photo=p['img'], caption=f"**{p['name']}**\n{p['price']}", reply_markup=kb.as_markup(), parse_mode="Markdown")
        await callback.message.delete()

@dp.callback_query(F.data == "to_main")
async def to_main(callback: types.CallbackQuery):
    await callback.message.delete()
    await start(callback.message)

# Оформление заказа (как в прошлом коде)
@dp.callback_query(F.data.startswith("buy_"))
async def choose_bank(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(product=PRODUCTS[int(callback.data.split("_")[1])]['name'])
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="Alif Bank 🟢", callback_data="set_bank_Alif"))
    kb.row(types.InlineKeyboardButton(text="Eskhata Bank 🔴", callback_data="set_bank_Eskhata"))
    kb.row(types.InlineKeyboardButton(text="Dushanbe City 🟡", callback_data="set_bank_DC"))
    await callback.message.answer("Выберите банк:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("set_bank_"))
async def start_order(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(bank=callback.data.split("_")[2])
    await callback.message.answer("Введите Ваше имя:")
    await state.set_state(OrderState.waiting_for_name)

@dp.message(OrderState.waiting_for_name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите номер (+992XXXXXXXXX):")
    await state.set_state(OrderState.waiting_for_phone)

@dp.message(OrderState.waiting_for_phone)
async def get_phone(message: types.Message, state: FSMContext):
    if re.fullmatch(r"^\+992\d{9}$", message.text):
        await state.update_data(phone=message.text)
        await message.answer("Введите адрес:")
        await state.set_state(OrderState.waiting_for_address)
    else:
        await message.answer("❌ Формат: +992 и 9 цифр.")

@dp.message(OrderState.waiting_for_address)
async def get_address(message: types.Message, state: FSMContext):
    data = await state.get_data()
    order_msg = f"🆕 **ЗАКАЗ!**\nТовар: {data['product']}\nИмя: {data['name']}\nТел: {data['phone']}\nАдрес: {message.text}\nБанк: {data['bank']}"
    await bot.send_message(ADMIN_ID, order_msg)
    await message.answer("✅ **Заказ сделан!** Ожидайте.", reply_markup=main_kb())
    await state.clear()

# --- АДМИН-ПАНЕЛЬ ---

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast"))
        await message.answer("⚡ **Панель администратора Mi Texno**", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "admin_broadcast")
async def broadcast_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Введите текст рассылки (его получат все юзеры):")
    await state.set_state(AdminState.waiting_for_broadcast_text)

@dp.message(AdminState.waiting_for_broadcast_text)
async def broadcast_finish(message: types.Message, state: FSMContext):
    users = get_all_users()
    count = 0
    for user_id in users:
        try:
            await bot.send_message(user_id, message.text)
            count += 1
        except:
            pass
    await message.answer(f"✅ Рассылка завершена! Отправлено {count} пользователям.")
    await state.clear()

async def main():
    init_db() # Запуск БД
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
