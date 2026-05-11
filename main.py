import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
    InputMediaPhoto
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
import json

# ========================
# НАСТРОЙКИ
# ========================
BOT_TOKEN = "8709726103:AAEqLzikyRxkusEyulxhvmL5sJ1Ivcb_THs"
ADMIN_IDS = [6362382479]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ========================
# БАЗА ДАННЫХ (JSON-файл)
# ========================
DB_FILE = "catalog.json"

def load_db() -> dict:
    if not os.path.exists(DB_FILE):
        return {"categories": {}}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data: dict):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def init_db():
    if not os.path.exists(DB_FILE):
        save_db({"categories": {}})

# ========================
# СТЕЙТЫ ДЛЯ АДМИНКИ
# ========================
class AdminStates(StatesGroup):
    waiting_category_name = State()
    waiting_product_category = State()
    waiting_product_name = State()
    waiting_product_photos = State()
    waiting_product_description = State()
    deleting_category = State()
    deleting_product = State()

# ========================
# КЛАВИАТУРЫ
# ========================
def main_menu_kb():
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛍 Каталог")],
            [KeyboardButton(text="⚙️ Админка")]
        ],
        resize_keyboard=True
    )
    return kb

def catalog_kb():
    db = load_db()
    builder = InlineKeyboardBuilder()
    categories = db.get("categories", {})
    if not categories:
        builder.button(text="Каталог пуст", callback_data="empty")
    else:
        for cat_name in categories:
            builder.button(text=f"📁 {cat_name}", callback_data=f"cat:{cat_name}")
        builder.adjust(2)
    return builder.as_markup()

def products_kb(category: str):
    db = load_db()
    products = db["categories"].get(category, {})
    builder = InlineKeyboardBuilder()
    for prod_name in products:
        builder.button(text=f"🛒 {prod_name}", callback_data=f"prod:{category}:{prod_name}:0")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_catalog"))
    return builder.as_markup()

def product_photo_kb(category: str, product: str, index: int, total: int):
    builder = InlineKeyboardBuilder()
    row = []
    if index > 0:
        row.append(InlineKeyboardButton(text="◀️ Пред.", callback_data=f"prod:{category}:{product}:{index - 1}"))
    row.append(InlineKeyboardButton(text=f"{index + 1}/{total}", callback_data="noop"))
    if index < total - 1:
        row.append(InlineKeyboardButton(text="След. ▶️", callback_data=f"prod:{category}:{product}:{index + 1}"))
    builder.row(*row)
    builder.row(InlineKeyboardButton(text="◀️ Назад к товарам", callback_data=f"cat:{category}"))
    return builder.as_markup()

def admin_main_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить категорию", callback_data="admin_add_category")
    builder.button(text="➕ Добавить товар", callback_data="admin_add_product")
    builder.button(text="🗑 Удалить категорию", callback_data="admin_del_category")
    builder.button(text="🗑 Удалить товар", callback_data="admin_del_product")
    builder.button(text="📋 Список каталога", callback_data="admin_list")
    builder.adjust(1)
    return builder.as_markup()

def admin_category_select_kb(action: str):
    db = load_db()
    builder = InlineKeyboardBuilder()
    for cat_name in db["categories"]:
        builder.button(text=cat_name, callback_data=f"{action}:{cat_name}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"))
    return builder.as_markup()

def cancel_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="admin_cancel")
    return builder.as_markup()

# ========================
# КОМАНДЫ
# ========================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 Добро пожаловать в магазин!\nВыберите раздел:",
        reply_markup=main_menu_kb()
    )

# ========================
# КАТАЛОГ
# ========================
@dp.message(F.text == "🛍 Каталог")
async def show_catalog(message: types.Message):
    await message.answer("📂 Выберите категорию:", reply_markup=catalog_kb())

@dp.callback_query(F.data == "back_to_catalog")
async def back_to_catalog(callback: types.CallbackQuery):
    await callback.message.edit_text("📂 Выберите категорию:", reply_markup=catalog_kb())

@dp.callback_query(F.data.startswith("cat:"))
async def show_category(callback: types.CallbackQuery):
    category = callback.data.split(":", 1)[1]
    db = load_db()
    products = db["categories"].get(category, {})
    if not products:
        await callback.answer("В этой категории пока нет товаров.", show_alert=True)
        return
    await callback.message.edit_text(
        f"📁 <b>{category}</b>\nВыберите товар:",
        reply_markup=products_kb(category),
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("prod:"))
async def show_product(callback: types.CallbackQuery):
    parts = callback.data.split(":")
    category = parts[1]
    product = parts[2]
    index = int(parts[3])

    db = load_db()
    product_data = db["categories"].get(category, {}).get(product)
    if not product_data:
        await callback.answer("Товар не найден.", show_alert=True)
        return

    photos = product_data.get("photos", [])
    description = product_data.get("description", "")
    total = len(photos)

    if total == 0:
        await callback.answer("У этого товара нет фото.", show_alert=True)
        return

    index = max(0, min(index, total - 1))
    photo_id = photos[index]
    caption = f"<b>{product}</b>\n{description}\n\n📸 Фото {index + 1} из {total}"

    kb = product_photo_kb(category, product, index, total)

    try:
        if callback.message.photo:
            await callback.message.edit_media(
                media=InputMediaPhoto(media=photo_id, caption=caption, parse_mode="HTML"),
                reply_markup=kb
            )
        else:
            await callback.message.delete()
            await callback.message.answer_photo(
                photo=photo_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=kb
            )
    except Exception:
        await callback.message.answer_photo(
            photo=photo_id,
            caption=caption,
            parse_mode="HTML",
            reply_markup=kb
        )

@dp.callback_query(F.data == "noop")
async def noop(callback: types.CallbackQuery):
    await callback.answer()

# ========================
# АДМИНКА
# ========================
def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

@dp.message(F.text == "⚙️ Админка")
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет доступа к админке.")
        return
    await message.answer("⚙️ <b>Панель администратора</b>", reply_markup=admin_main_kb(), parse_mode="HTML")

@dp.callback_query(F.data == "admin_cancel")
async def admin_cancel(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("⚙️ <b>Панель администратора</b>", reply_markup=admin_main_kb(), parse_mode="HTML")

# --- Добавить категорию ---
@dp.callback_query(F.data == "admin_add_category")
async def admin_add_category_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    await state.set_state(AdminStates.waiting_category_name)
    await callback.message.edit_text("✏️ Введите название новой категории:", reply_markup=cancel_kb())

@dp.message(StateFilter(AdminStates.waiting_category_name))
async def admin_add_category_done(message: types.Message, state: FSMContext):
    cat_name = message.text.strip()
    db = load_db()
    if cat_name in db["categories"]:
        await message.answer(f"⚠️ Категория «{cat_name}» уже существует.", reply_markup=admin_main_kb())
    else:
        db["categories"][cat_name] = {}
        save_db(db)
        await message.answer(f"✅ Категория «{cat_name}» создана!", reply_markup=admin_main_kb())
    await state.clear()

# --- Добавить товар ---
@dp.callback_query(F.data == "admin_add_product")
async def admin_add_product_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    db = load_db()
    if not db["categories"]:
        await callback.answer("Сначала создайте категорию!", show_alert=True)
        return
    await state.set_state(AdminStates.waiting_product_category)
    await callback.message.edit_text("📁 Выберите категорию для товара:", reply_markup=admin_category_select_kb("select_cat_for_prod"))

@dp.callback_query(F.data.startswith("select_cat_for_prod:"))
async def admin_product_category_chosen(callback: types.CallbackQuery, state: FSMContext):
    category = callback.data.split(":", 1)[1]
    await state.update_data(category=category)
    await state.set_state(AdminStates.waiting_product_name)
    await callback.message.edit_text(f"✏️ Введите название товара для категории «{category}»:", reply_markup=cancel_kb())

@dp.message(StateFilter(AdminStates.waiting_product_name))
async def admin_product_name_done(message: types.Message, state: FSMContext):
    prod_name = message.text.strip()
    await state.update_data(product_name=prod_name, photos=[])
    await state.set_state(AdminStates.waiting_product_photos)
    await message.answer(
        f"📸 Отправьте фото для товара «{prod_name}».\n"
        "Можно отправить несколько фото по одному.\n"
        "Когда все фото загружены — напишите /done",
        reply_markup=cancel_kb()
    )

@dp.message(StateFilter(AdminStates.waiting_product_photos), F.photo)
async def admin_product_photo_received(message: types.Message, state: FSMContext):
    data = await state.get_data()
    photos = data.get("photos", [])
    file_id = message.photo[-1].file_id
    photos.append(file_id)
    await state.update_data(photos=photos)
    await message.answer(f"✅ Фото {len(photos)} добавлено. Отправьте ещё или напишите /done")

@dp.message(StateFilter(AdminStates.waiting_product_photos), Command("done"))
async def admin_product_photos_done(message: types.Message, state: FSMContext):
    await state.set_state(AdminStates.waiting_product_description)
    await message.answer("📝 Введите описание товара (или /skip чтобы пропустить):")

@dp.message(StateFilter(AdminStates.waiting_product_description))
async def admin_product_description_done(message: types.Message, state: FSMContext):
    description = "" if message.text == "/skip" else message.text.strip()
    data = await state.get_data()
    category = data["category"]
    product_name = data["product_name"]
    photos = data.get("photos", [])

    db = load_db()
    db["categories"][category][product_name] = {
        "photos": photos,
        "description": description
    }
    save_db(db)

    await message.answer(
        f"✅ Товар «{product_name}» добавлен в «{category}»!\n"
        f"Фото: {len(photos)} шт.",
        reply_markup=admin_main_kb()
    )
    await state.clear()

# --- Удалить категорию ---
@dp.callback_query(F.data == "admin_del_category")
async def admin_del_category_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    db = load_db()
    if not db["categories"]:
        await callback.answer("Нет категорий для удаления.", show_alert=True)
        return
    await state.set_state(AdminStates.deleting_category)
    await callback.message.edit_text("🗑 Выберите категорию для удаления:", reply_markup=admin_category_select_kb("del_cat"))

@dp.callback_query(F.data.startswith("del_cat:"))
async def admin_del_category_done(callback: types.CallbackQuery, state: FSMContext):
    category = callback.data.split(":", 1)[1]
    db = load_db()
    if category in db["categories"]:
        del db["categories"][category]
        save_db(db)
        await callback.message.edit_text(f"✅ Категория «{category}» удалена.", reply_markup=admin_main_kb())
    else:
        await callback.answer("Категория не найдена.", show_alert=True)
    await state.clear()

# --- Удалить товар ---
@dp.callback_query(F.data == "admin_del_product")
async def admin_del_product_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return
    db = load_db()
    if not db["categories"]:
        await callback.answer("Нет категорий.", show_alert=True)
        return
    await state.set_state(AdminStates.deleting_product)
    await callback.message.edit_text("📁 Выберите категорию:", reply_markup=admin_category_select_kb("del_prod_cat"))

@dp.callback_query(F.data.startswith("del_prod_cat:"))
async def admin_del_product_category_chosen(callback: types.CallbackQuery, state: FSMContext):
    category = callback.data.split(":", 1)[1]
    await state.update_data(del_category=category)
    db = load_db()
    products = db["categories"].get(category, {})
    if not products:
        await callback.answer("В этой категории нет товаров.", show_alert=True)
        return
    builder = InlineKeyboardBuilder()
    for prod_name in products:
        builder.button(text=prod_name, callback_data=f"del_prod:{category}:{prod_name}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="admin_cancel"))
    await callback.message.edit_text(f"🗑 Выберите товар для удаления из «{category}»:", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("del_prod:"))
async def admin_del_product_done(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    category = parts[1]
    product = parts[2]
    db = load_db()
    if product in db["categories"].get(category, {}):
        del db["categories"][category][product]
        save_db(db)
        await callback.message.edit_text(f"✅ Товар «{product}» удалён из «{category}».", reply_markup=admin_main_kb())
    else:
        await callback.answer("Товар не найден.", show_alert=True)
    await state.clear()

# --- Список каталога ---
@dp.callback_query(F.data == "admin_list")
async def admin_list(callback: types.CallbackQuery):
    db = load_db()
    text = "📋 <b>Текущий каталог:</b>\n\n"
    if not db["categories"]:
        text += "Каталог пуст."
    else:
        for cat_name, products in db["categories"].items():
            text += f"📁 <b>{cat_name}</b> ({len(products)} товаров)\n"
            for prod_name, prod_data in products.items():
                photos_count = len(prod_data.get("photos", []))
                text += f"  └ 🛒 {prod_name} [{photos_count} фото]\n"
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="admin_back")
    await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")

@dp.callback_query(F.data == "admin_back")
async def admin_back(callback: types.CallbackQuery):
    await callback.message.edit_text("⚙️ <b>Панель администратора</b>", reply_markup=admin_main_kb(), parse_mode="HTML")

# ========================
# ЗАПУСК
# ========================
async def main():
    init_db()
    logger.info("Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
