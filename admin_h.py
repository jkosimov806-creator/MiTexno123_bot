import asyncio
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from config import ADMIN_ID, SPREADSHEET_ID, CREDENTIALS_FILE
from database import add_item, delete_item, get_item, get_all_user_ids, add_promo, sync_items_from_sheet
from kb import admin_kb

import gspread
from oauth2client.service_account import ServiceAccountCredentials

router = Router()

SHEET_NAMES = [
    "Кондиционеры и обогреватели",
    "Телевизоры",
    "Стиральная машина",
    "Холодильник",
    "Очистители, увлажнители воздуха",
    "Всё для дома",
    "Пылесос и фен",
    "Гаджеты",
    "Мониторы и дисплеи",
    "Камеры",
]


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def get_all_products():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_key(SPREADSHEET_ID)

    all_items = []
    for sheet_name in SHEET_NAMES:
        try:
            sheet = spreadsheet.worksheet(sheet_name)
            rows = sheet.get_all_values()
            # строка 1 = название категории, строка 2 = заголовки, строки 3+ = товары
            for row in rows[2:]:
                if not row or not row[0].strip():
                    continue
                name = row[0].strip()
                stock = row[1].strip() if len(row) > 1 else "0"
                price = row[2].strip() if len(row) > 2 else "0"
                photo = row[4].strip() if len(row) > 4 else ""
                if not price.isdigit():
                    price = "0"
                if not stock.isdigit():
                    stock = "0"
                all_items.append({
                    "name": name,
                    "price": int(price),
                    "description": f"В наличии: {stock} шт.",
                    "category": sheet_name,
                    "photo": photo,
                })
        except Exception:
            continue

    return all_items


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


# ─── Синхронизация Google Sheets → SQLite ─────────────────────────────────────

@router.callback_query(F.data == "admin_sync")
async def sync_catalog(c: types.CallbackQuery):
    if not is_admin(c.from_user.id):
        return
    await c.answer()
    msg = await c.message.answer("⏳ Синхронизирую каталог с Google Sheets...")
    try:
        items = get_all_products()
        count = sync_items_from_sheet(items)
        await msg.edit_text(
            f"✅ Синхронизация завершена!\n"
            f"Загружено товаров: <b>{count}</b>",
            reply_markup=admin_kb(),
            parse_mode="HTML",
        )
    except Exception as e:
        await msg.edit_text(
            f"❌ Ошибка синхронизации:\n<code>{e}</code>",
            reply_markup=admin_kb(),
            parse_mode="HTML",
        )


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
