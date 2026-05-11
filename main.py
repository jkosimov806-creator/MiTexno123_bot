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
    waiting_for_quantity = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()
    waiting_for_bank = State()
    waiting_for_check = State()

class AdminState(StatesGroup):
    waiting_for_broadcast = State()
    add_item_name, add_item_price, add_item_desc, add_item_photo = State(), State(), State(), State(), State()

# --- БАЗА (Товары и Юзеры) ---
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
    kb.row(types.InlineKeyboardButton(text="📦 Перейти в каталог", callback_data="catalog_0"))
    kb.row(types.InlineKeyboardButton(text="🛒 Моя корзина", callback_data="view_cart"))
    kb.row(types.InlineKeyboardButton(text="🆘 Служба поддержки", url=SUPPORT_LINK))
    if user_id == ADMIN_ID:
        kb.row(types.InlineKeyboardButton(text="⚙️ Панель администратора", callback_data="admin_menu"))
    return kb.as_markup()

@dp.message(CommandStart())
async def start(message: types.Message):
    db_query('INSERT OR IGNORE INTO users VALUES (?)', (message.from_user.id,))
    await message.answer(
        f"**Вас приветствует Mi Texno — магазин оригинальной электроники** 📱\n\n"
        f"Мы предлагаем широкий ассортимент высокотехнологичных решений для Вашего комфорта.\n\n"
        f"**Пожалуйста, выберите интересующий Вас раздел:**",
        reply_markup=main_kb(message.from_user.id), parse_mode="Markdown"
    )

# --- КАТАЛОГ И ВЫБОР КОЛИЧЕСТВА ---
@dp.callback_query(F.data.startswith("catalog_"))
async def show_catalog(c: types.CallbackQuery):
    items = db_query('SELECT * FROM items', fetch=True)
    if not items: return await c.answer("В данный момент каталог пуст.", show_alert=True)
    idx = int(c.data.split("_")[1]); item = items[idx]
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ Добавить в корзину", callback_data=f"to_cart_{item[0]}"))
    nav = [types.InlineKeyboardButton(text=f"•{i+1}•" if i == idx else str(i+1), callback_data=f"catalog_{i}") for i in range(len(items))]
    kb.row(*nav)
    kb.row(types.InlineKeyboardButton(text="⬅️ Вернуться в главное меню", callback_data="to_main"))
    
    caption = f"**{item[1]}**\n\n{item[3] if item[3] else ''}\n\n**Стоимость:** {item[2]}"
    await c.message.delete()
    await c.message.answer_photo(photo=item[4], caption=caption, reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("to_cart_"))
async def ask_quantity(c: types.CallbackQuery, state: FSMContext):
    item_id = c.data.split("_")[2]
    await state.update_data(current_item_id=item_id)
    
    kb = InlineKeyboardBuilder()
    for i in range(1, 6):
        kb.add(types.InlineKeyboardButton(text=str(i), callback_data=f"qty_{i}"))
    kb.row(types.InlineKeyboardButton(text="❌ Отмена", callback_data="catalog_0"))
    
    await c.message.answer("Укажите необходимое количество товара:", reply_markup=kb.as_markup())
    await state.set_state(OrderState.waiting_for_quantity)

@dp.callback_query(OrderState.waiting_for_quantity, F.data.startswith("qty_"))
async def add_to_cart_done(c: types.CallbackQuery, state: FSMContext):
    qty = int(c.data.split("_")[1])
    data = await state.get_data()
    item_id = data['current_item_id']
    
    # Сохраняем в память корзины (в контекст состояния)
    cart = data.get('cart', {})
    cart[item_id] = cart.get(item_id, 0) + qty
    await state.update_data(cart=cart)
    
    await c.answer(f"Товар успешно добавлен в корзину ({qty} шт.)", show_alert=False)
    await show_catalog(c) # Возвращаем в каталог

# --- ПРОСМОТР КОРЗИНЫ ---
@dp.callback_query(F.data == "view_cart")
async def view_cart(c: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    cart = data.get('cart', {})
    if not cart: return await c.answer("Ваша корзина пока пуста.", show_alert=True)
    
    text = "**🛒 Ваша корзина:**\n\n"
    for item_id, qty in cart.items():
        item = db_query('SELECT name, price FROM items WHERE id = ?', (item_id,), fetch_one=True)
        text += f"• {item[0]} — {qty} шт. ({item[1]})\n"
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout"))
    kb.row(types.InlineKeyboardButton(text="🗑 Очистить корзину", callback_data="clear_cart"))
    kb.row(types.InlineKeyboardButton(text="⬅️ Назад", callback_data="to_main"))
    
    await c.message.answer(text, reply_markup=kb.as_markup(), parse_mode="Markdown")

# --- ОФОРМЛЕНИЕ ЗАКАЗА ---
@dp.callback_query(F.data == "checkout")
async def start_checkout(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("Для оформления доставки, пожалуйста, укажите Ваше имя:")
    await state.set_state(OrderState.waiting_for_name)

@dp.message(OrderState.waiting_for_name)
async def checkout_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("Введите Ваш контактный номер телефона в формате: +992XXXXXXXXX")
    await state.set_state(OrderState.waiting_for_phone)

@dp.message(OrderState.waiting_for_phone)
async def checkout_phone(m: types.Message, state: FSMContext):
    if re.fullmatch(r"^\+992\d{9}$", m.text):
        await state.update_data(phone=m.text)
        await m.answer("Укажите точный адрес доставки:")
        await state.set_state(OrderState.waiting_for_address)
    else:
        await m.answer("❌ Некорректный формат номера. Пожалуйста, введите 9 цифр после +992.")

@dp.message(OrderState.waiting_for_address)
async def checkout_address(m: types.Message, state: FSMContext):
    await state.update_data(address=m.text)
    kb = InlineKeyboardBuilder()
    for b in ["Alif Bank 🟢", "Eskhata Bank 🔴", "Dushanbe City 🟡"]:
        kb.row(types.InlineKeyboardButton(text=b, callback_data=f"pay_{b}"))
    await m.answer("Выберите удобный для Вас банк для совершения оплаты:", reply_markup=kb.as_markup())
    await state.set_state(OrderState.waiting_for_bank)

@dp.callback_query(OrderState.waiting_for_bank)
async def checkout_bank(c: types.CallbackQuery, state: FSMContext):
    bank = c.data.split("_")[1]
    await state.update_data(bank=bank)
    await c.message.answer(
        f"**Реквизиты для оплаты ({bank}):**\n`+992928663510`\n\n"
        f"Пожалуйста, совершите перевод и **отправьте скриншот чека** в данный чат для подтверждения заказа.",
        parse_mode="Markdown"
    )
    await state.set_state(OrderState.waiting_for_check)

@dp.message(OrderState.waiting_for_check, F.photo)
async def checkout_finish(m: types.Message, state: FSMContext):
    d = await state.get_data()
    cart_text = ""
    for item_id, qty in d['cart'].items():
        item = db_query('SELECT name FROM items WHERE id = ?', (item_id,), fetch_one=True)
        cart_text += f"- {item[0]}: {qty} шт.\n"

    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"adm_ok_{m.from_user.id}"))
    kb.row(types.InlineKeyboardButton(text="❌ Отклонить", callback_data=f"adm_no_{m.from_user.id}"))
    
    admin_msg = (
        f"🆕 **НОВЫЙ ЗАКАЗ!**\n\n"
        f"🛒 **Товары:**\n{cart_text}\n"
        f"👤 Клиент: {d['name']}\n"
        f"📞 Номер: {d['phone']}\n"
        f"🏠 Адрес: {d['address']}\n"
        f"💳 Банк: {d['bank']}"
    )
    await bot.send_photo(ADMIN_ID, photo=m.photo[-1].file_id, caption=admin_msg, reply_markup=kb.as_markup())
    await m.answer("✅ **Благодарим за заказ!**\nВаш чек принят в обработку. Менеджер свяжется с Вами после проверки платежа.", reply_markup=main_kb(m.from_user.id))
    # Очищаем только данные заказа, корзину можно оставить или тоже очистить
    await state.update_data(cart={}) 

# --- АДМИН-ЛОГИКА (УВЕДОМЛЕНИЯ) ---
@dp.callback_query(F.data.startswith("adm_"))
async def admin_decision(c: types.CallbackQuery):
    action = c.data.split("_")[1]
    user_id = int(c.data.split("_")[2])
    if action == "ok":
        await bot.send_message(user_id, "✨ **Ваш заказ успешно подтвержден!** Мы уже готовим его к отправке.")
        await c.message.edit_caption(caption=c.message.caption + "\n\n✅ [ОДОБРЕНО]")
    else:
        await bot.send_message(user_id, "⚠️ **Ваш заказ отклонен.** Пожалуйста, свяжитесь с поддержкой для уточнения деталей.")
        await c.message.edit_caption(caption=c.message.caption + "\n\n❌ [ОТКЛОНЕНО]")

# Остальная логика админки (добавление товаров, рассылка) - без изменений...
# [Вставь сюда функции admin_menu, broadcast, add_item из предыдущего кода]

@dp.callback_query(F.data == "to_main")
async def back_to_main(c: types.CallbackQuery):
    await c.message.delete()
    await start(c.message)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
