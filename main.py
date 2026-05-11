import asyncio, re, sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Подключаем настройки и твой новый файл поддержки
from config import TOKEN, ADMIN_ID, SUPPORT_LINK
import support 

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- СОСТОЯНИЯ ---
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

# --- ГЛАВНОЕ МЕНЮ ---
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
        f"◈ **MI TEXNO | Premium Store** 📱\n━━━━━━━━━━━━━━━━━━━━\nЗдравствуйте! Выберите раздел для навигации:",
        reply_markup=main_kb(message.from_user.id), parse_mode="Markdown"
    )

# --- КАТАЛОГ ---
@dp.callback_query(F.data.startswith("catalog_"))
async def show_catalog(c: types.CallbackQuery):
    items = db_query('SELECT * FROM items', fetch=True)
    if not items: return await c.answer("Каталог пуст.", show_alert=True)
    idx = int(c.data.split("_")[-1]) % len(items); item = items[idx]
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ В КОРЗИНУ", callback_data=f"start_count_{item[0]}"))
    nav = [types.InlineKeyboardButton(text=f"•{i+1}•" if i == idx else str(i+1), callback_data=f"catalog_{i}") for i in range(len(items))]
    kb.row(*nav)
    kb.row(types.InlineKeyboardButton(text="⬅️ В МЕНЮ", callback_data="to_main"))
    await c.message.delete()
    await c.message.answer_photo(photo=item[4], caption=f"┃ **{item[1]}**\n┃ {item[3]}\n\n┃ ◈ **Цена:** {item[2]} TJS", reply_markup=kb.as_markup(), parse_mode="Markdown")

# --- ЛОГИКА ОФОРМЛЕНИЯ И АДМИНКИ (ОСТАЕТСЯ КАК БЫЛО) ---
# ... [Тут весь код заказа, корзины и админки, который мы писали] ...

@dp.callback_query(F.data == "to_main")
async def back_to_main(c: types.CallbackQuery):
    try: await c.message.delete()
    except: pass
    await start(c.message)

# --- ЗАПУСК ---
async def main():
    # Инициализация таблиц
    with sqlite3.connect('mi_texno.db') as conn:
        conn.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)')
        conn.execute('CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, price INTEGER, desc TEXT, photo TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, discount INTEGER)')
    
    # ПРИВЯЗЫВАЕМ ФАЙЛ ПОДДЕРЖКИ
    dp.include_router(support.router)
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
