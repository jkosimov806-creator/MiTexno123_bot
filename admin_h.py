import asyncio
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_ID
from database import add_item, delete_item, get_item, get_all_user_ids, add_promo
from kb import admin_kb

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


class AddItemState(StatesGroup):
    name = State()
    price = State()
    desc = State()
    category = State()
    photo = State()


class AddPromoState(StatesGroup):
    code = State()
    discount = State()


class BroadcastState(StatesGroup):
    text = State()


class DelItemState(StatesGroup):
    item_id = State()


# ─── Панель ───────────────────────────────────────────────────────────────────

@router.message(Command("admin"))
async def admin_panel(m: types.Message):
    if not is_admin(m.from_user.id):
        return
    await m.answer("<b>🛠 ПАНЕЛЬ УПРАВЛЕНИЯ</b>", reply_markup=admin_kb(), parse_mode="HTML")


# ─── Добавить товар ───────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_add_item")
async def ad_start(c: types.CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id): return
    await c.message.answer("📝 Название товара:")
    await state.set_state(AddItemState.name)


@router.message(AddItemState.name)
async def ad_name(m: types.Message, state: FSMContext):
    await state.update_data(name=m.text.strip())
    await m.answer("💰 Цена (число):")
    await state.set_state(AddItemState.price)


@router.message(AddItemState.price)
async def ad_price(m: types.Message, state: FSMContext):
    if not m.text.isdigit():
        await m.answer("❌ Введите целое число:"); return
    await state.update_data(price=int(m.text))
    await m.answer("📄 Описание (или /skip):")
    await state.set_state(AddItemState.desc)


@router.message(AddItemState.desc)
async def ad_desc(m: types.Message, state: FSMContext):
    await state.update_data(desc="" if m.text == "/skip" else m.text.strip())
    await m.answer("📂 Категория:")
    await state.set_state(AddItemState.category)


@router.message(AddItemState.category)
async def ad_cat(m: types.Message, state: FSMContext):
    await state.update_data(category=m.text.strip())
    await m.answer("🖼 Пришлите фото:")
    await state.set_state(AddItemState.photo)


@router.message(AddItemState.photo, F.photo)
async def ad_photo(m: types.Message, state: FSMContext):
    data = await state.get_data()
    add_item(data["name"], data["price"], data.get("desc", ""), data["category"], m.photo[-1].file_id)
    await m.answer(f"✅ Товар <b>{data['name']}</b> добавлен!", reply_markup=admin_kb(), parse_mode="HTML")
    await state.clear()


@router.message(AddItemState.photo)
async def ad_photo_wrong(m: types.Message):
    await m.answer("❌ Нужно прислать фото.")


# ─── Удалить товар ────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_del_item")
async def del_start(c: types.CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id): return
    await c.message.answer("🗑 Введите ID товара:")
    await state.set_state(DelItemState.item_id)


@router.message(DelItemState.item_id)
async def del_do(m: types.Message, state: FSMContext):
    if not m.text.isdigit():
        await m.answer("❌ Введите числовой ID:"); return
    item = get_item(int(m.text))
    if not item:
        await m.answer("❌ Товар не найден.")
        await state.clear(); return
    delete_item(item["id"])
    await m.answer(f"✅ Товар «{item['name']}» удалён.", reply_markup=admin_kb())
    await state.clear()


# ─── Промокод ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_add_promo")
async def promo_start(c: types.CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id): return
    await c.message.answer("🏷 Код промокода:")
    await state.set_state(AddPromoState.code)


@router.message(AddPromoState.code)
async def promo_code(m: types.Message, state: FSMContext):
    await state.update_data(code=m.text.strip().upper())
    await m.answer("💯 Скидка в % (1–100):")
    await state.set_state(AddPromoState.discount)


@router.message(AddPromoState.discount)
async def promo_discount(m: types.Message, state: FSMContext):
    if not m.text.isdigit() or not (1 <= int(m.text) <= 100):
        await m.answer("❌ Введите число от 1 до 100:"); return
    data = await state.get_data()
    add_promo(data["code"], int(m.text))
    await m.answer(f"✅ Промокод <b>{data['code']}</b> на {m.text}% создан!", reply_markup=admin_kb(), parse_mode="HTML")
    await state.clear()


# ─── Рассылка ─────────────────────────────────────────────────────────────────

@router.callback_query(F.data == "admin_broadcast")
async def br_start(c: types.CallbackQuery, state: FSMContext):
    if not is_admin(c.from_user.id): return
    await c.message.answer("📢 Текст рассылки:")
    await state.set_state(BroadcastState.text)


@router.message(BroadcastState.text)
async def br_do(m: types.Message, state: FSMContext):
    await state.clear()
    users = get_all_user_ids()
    sent = failed = 0
    status = await m.answer(f"⏳ Рассылка... 0/{len(users)}")
    for i, uid in enumerate(users, 1):
        try:
            await m.bot.send_message(uid, m.text, parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
        if i % 20 == 0:
            try: await status.edit_text(f"⏳ Рассылка... {i}/{len(users)}")
            except Exception: pass
        await asyncio.sleep(0.05)
    await status.edit_text(f"✅ Готово! Доставлено: {sent} | Ошибок: {failed}")
