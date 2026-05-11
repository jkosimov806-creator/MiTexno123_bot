from aiogram import Router, F, types
from config import ITEMS_PER_PAGE
from database import get_categories, get_items_by_category, get_item, cart_add
from kb import categories_kb, items_kb, item_detail_kb

router = Router()


@router.callback_query(F.data == "catalog")
async def show_catalog(c: types.CallbackQuery):
    cats = get_categories()
    if not cats:
        await c.answer("Каталог пока пуст 😔", show_alert=True)
        return
    await c.message.edit_text(
        "<b>📦 КАТАЛОГ</b>\n━━━━━━━━━━━━━━━\nВыберите категорию:",
        reply_markup=categories_kb(cats), parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("cat:"))
async def show_category(c: types.CallbackQuery):
    await _show_page(c, c.data.split(":", 1)[1], 0)


@router.callback_query(F.data.startswith("page:"))
async def paginate(c: types.CallbackQuery):
    _, category, page_str = c.data.split(":", 2)
    await _show_page(c, category, int(page_str))


async def _show_page(c: types.CallbackQuery, category: str, page: int):
    all_items = get_items_by_category(category)
    if not all_items:
        await c.answer("В этой категории нет товаров", show_alert=True)
        return
    total_pages = max(1, -(-len(all_items) // ITEMS_PER_PAGE))
    page = max(0, min(page, total_pages - 1))
    chunk = all_items[page * ITEMS_PER_PAGE:(page + 1) * ITEMS_PER_PAGE]
    await c.message.edit_text(
        f"<b>📂 {category}</b>\n━━━━━━━━━━━━━━━\nТоваров: {len(all_items)}",
        reply_markup=items_kb(chunk, page, total_pages, category),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("item:"))
async def show_item(c: types.CallbackQuery):
    item = get_item(int(c.data.split(":")[1]))
    if not item:
        await c.answer("Товар не найден", show_alert=True)
        return
    text = (
        f"<b>{item['name']}</b>\n━━━━━━━━━━━━━━━\n"
        f"💰 Цена: <b>{item['price']} ₽</b>\n"
        f"📂 Категория: {item['category']}\n\n"
        f"{item['description'] or ''}"
    )
    kb = item_detail_kb(item["id"], item["category"])
    if item["photo"]:
        try:
            await c.message.delete()
            await c.message.answer_photo(photo=item["photo"], caption=text,
                                         reply_markup=kb, parse_mode="HTML")
            return
        except Exception:
            pass
    await c.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("add_cart:"))
async def add_to_cart(c: types.CallbackQuery):
    item = get_item(int(c.data.split(":")[1]))
    if not item:
        await c.answer("Товар не найден", show_alert=True)
        return
    cart_add(c.from_user.id, item["id"])
    await c.answer(f"✅ «{item['name']}» добавлен в корзину!")


@router.callback_query(F.data == "noop")
async def noop(c: types.CallbackQuery):
    await c.answer()
