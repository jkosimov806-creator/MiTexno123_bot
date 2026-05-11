import asyncio
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import TOKEN, ADMIN_ID, SUPPORT_LINK

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Состояния заказа
class OrderState(StatesGroup):
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_address = State()

PRODUCTS = [
    {"id": 0, "name": "Xiaomi 14 Ultra", "price": "14500 c.", "desc": "Камера Leica.", "img": "https://media-amazon.com"},
    {"id": 1, "name": "iPhone 15 Pro Max", "price": "13200 c.", "desc": "Титан.", "img": "https://clck.ru"}
]

def main_kb():
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="📦 Каталог", callback_data="cat_0"))
    kb.row(types.InlineKeyboardButton(text="🆘 Поддержка", url=SUPPORT_LINK))
    return kb.as_markup()

@dp.message(CommandStart())
async def start(message: types.Message):
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
    kb.row(types.InlineKeyboardButton(text="1", callback_data="cat_0"), types.InlineKeyboardButton(text="2", callback_data="cat_1"))
    await callback.message.delete()
    await callback.message.answer_photo(photo=p['img'], caption=f"**{p['name']}**\n{p['price']}", reply_markup=kb.as_markup(), parse_mode="Markdown")

# Начало оформления
@dp.callback_query(F.data.startswith("buy_"))
async def start_order(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(product=PRODUCTS[int(callback.data.split("_")[1])]['name'])
    await callback.message.answer("Введите Ваше имя:")
    await state.set_state(OrderState.waiting_for_name)

@dp.message(OrderState.waiting_for_name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите Ваш номер (формат: +992XXXXXXXXX):")
    await state.set_state(OrderState.waiting_for_phone)

@dp.message(OrderState.waiting_for_phone)
async def get_phone(message: types.Message, state: FSMContext):
    # Проверка: начинается с +992 и дальше ровно 9 цифр
    if re.fullmatch(r"^\+992\d{9}$", message.text):
        await state.update_data(phone=message.text)
        await message.answer("Введите адрес доставки:")
        await state.set_state(OrderState.waiting_for_address)
    else:
        await message.answer("❌ Ошибка! Введите номер в формате +992 и 9 цифр.")

@dp.message(OrderState.waiting_for_address)
async def get_address(message: types.Message, state: FSMContext):
    data = await state.get_data()
    # Отправка админу
    order_text = f"🆕 **Новый заказ!**\nТовар: {data['product']}\nИмя: {data['name']}\nТел: {data['phone']}\nАдрес: {message.text}"
    await bot.send_message(ADMIN_ID, order_text)
    
    await message.answer("✅ **Вы сделали заказ!** Ожидайте подтверждения менеджером.", reply_markup=main_kb())
    await state.clear()

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
