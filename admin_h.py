from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import ADMIN_ID
from database import db_query

router = Router()

class AdminState(StatesGroup):
    broadcast = State()
    add_n, add_p, add_d, add_c, add_ph = State(), State(), State(), State(), State()

@router.message(Command("admin"))
async def admin_main(message: types.Message):
    if message.from_user.id != ADMIN_ID: return
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ ДОБАВИТЬ ТОВАР", callback_data="add_item"))
    kb.row(types.InlineKeyboardButton(text="📢 РАССЫЛКА", callback_data="broadcast"))
    await message.answer("<b>🛠 ПАНЕЛЬ УПРАВЛЕНИЯ MI TEXNO</b>", reply_markup=kb.as_markup(), parse_mode="HTML")

@router.callback_query(F.data == "add_item")
async def ad_add(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("Введите название товара:"); await state.set_state(AdminState.add_n)

@router.message(AdminState.add_n)
async def ad_n(m: types.Message, state: FSMContext):
    await state.update_data(n=m.text); await m.answer("Цена (только цифры):"); await state.set_state(AdminState.add_p)

@router.message(AdminState.add_p)
async def ad_p(m: types.Message, state: FSMContext):
    await state.update_data(p=m.text); await m.answer("Описание товара (/skip):"); await state.set_state(AdminState.add_d)

@router.message(AdminState.add_d)
async def ad_d(m: types.Message, state: FSMContext):
    d = "" if m.text == "/skip" else m.text
    await state.update_data(d=d); await m.answer("Введите название категории (categorie):"); await state.set_state(AdminState.add_c)

@router.message(AdminState.add_c)
async def ad_c(m: types.Message, state: FSMContext):
    await state.update_data(c=m.text); await m.answer("Пришлите фото товара:"); await state.set_state(AdminState.add_ph)

@router.message(AdminState.add_ph, F.photo)
async def ad_ph(m: types.Message, state: FSMContext):
    data = await state.get_data()
    db_query('INSERT INTO items (name, price, desc, categorie, photo) VALUES (?,?,?,?,?)', 
             (data['n'], int(data['p']), data['d'], data['c'], m.photo[-1].file_id))
    await m.answer(f"✅ Товар добавлен в категорию {data['c']}!"); await state.clear()
