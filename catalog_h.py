from aiogram import Router, F, types
from config import ITEMS_PER_PAGE
from database import get_categories, get_items_by_category, get_item, cart_add
from keyboards import categories_kb, items_kb, item_detail_kb, back_to_main_kb

router = Router()


@router.callback_query(F.data == "catalog")
async def show_catalog(c: types.CallbackQuery):
    cats = get_categories()
    if not cats:
        await c.answer("Каталог пока пуст 😔", show_alert=True)
        return
    await c.message.edit_text(
        "<b>📦 КАТАЛОГ</b>\n━━━━━━━━━━━━━━━\nВыберите категорию:",
        reply_markup=categories_kb(cats),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("cat:"))
async def show_category(c: types.CallbackQuery):
    category = c.data.split(":", 1)[1]
    await _show_page(c, category, 0)


@router.callback_query(F.data.startswith("page:"))
async def paginate(c: types.CallbackQuery):
    _, category, page_str = c.data.split(":", 2)
    await _show_page(c, category, int(page_str))


async def _show_page(c: types.CallbackQuery, category: str, page: int):
    all_items = get_items_by_category(category)
    if not all_items:
        await c.answer("В этой категории нет товаров", show_alert=True)
        return

    total_pages = max(1, -(-len(all_items) // ITEMS_PER_PAGE))  # ceil division
    page = max(0, min(page, total_pages - 1))
    slice_ = all_items[page * ITEMS_PER_PAGE : (page + 1) * ITEMS_PER_PAGE]

    text = f"<b>📂 {category}</b>\n━━━━━━━━━━━━━━━\nВсего товаров: {len(all_items)}"
    await c.message.edit_text(
        text,
        reply_markup=items_kb(slice_, page, total_pages, category),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("item:"))
async def show_item(c: types.CallbackQuery):
    item_id = int(c.data.split(":")[1])
    item = get_item(item_id)
    if not item:
        await c.answer("Товар не найден", show_alert=True)
        return

    text = (
        f"<b>{item['name']}</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"💰 Цена: <b>{item['price']} ₽</b>\n"
        f"📂 Категория: {item['category']}\n\n"
        f"{item['description'] or ''}"
    )
    kb = item_detail_kb(item_id, item["category"])

    if item["photo"]:
        try:
            await c.message.delete()
            await c.message.answer_photo(
                photo=item["photo"],
                caption=text,
                reply_markup=kb,
                parse_mode="HTML",
            )
            return
        except Exception:
            pass

    await c.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("add_cart:"))
async def add_to_cart(c: types.CallbackQuery):
    item_id = int(c.data.split(":")[1])
    item = get_item(item_id)
    if not item:
        await c.answer("Товар не найден", show_alert=True)
        return
    cart_add(c.from_user.id, item_id)
    await c.answer(f"✅ «{item['name']}» добавлен в корзину!")


@router.callback_query(F.data == "noop")
async def noop(c: types.CallbackQuery):
    await c.answer()
