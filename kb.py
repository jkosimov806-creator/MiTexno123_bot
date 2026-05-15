from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def main_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📦 КАТАЛОГ", callback_data="catalog"))
    kb.row(InlineKeyboardButton(text="🛒 КОРЗИНА", callback_data="view_cart"))
    kb.row(InlineKeyboardButton(text="🛡 ПОДДЕРЖКА", callback_data="support"))
    return kb.as_markup()


def back_main_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="⬅️ На главную", callback_data="to_main"))
    return kb.as_markup()


def categories_kb(categories: list[str]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i, cat in enumerate(categories):
        # используем индекс вместо названия чтобы не превысить лимит 64 символа
        kb.row(InlineKeyboardButton(text=f"📂 {cat}", callback_data=f"cat:{i}"))
    kb.row(InlineKeyboardButton(text="⬅️ На главную", callback_data="to_main"))
    return kb.as_markup()


def items_kb(items, page: int, total_pages: int, cat_index: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for item in items:
        kb.row(InlineKeyboardButton(
            text=f"{item['name']} — {item['price']} ₽",
            callback_data=f"item:{item['id']}",
        ))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="◀️", callback_data=f"page:{cat_index}:{page - 1}"))
    nav.append(InlineKeyboardButton(text=f"{page + 1}/{total_pages}", callback_data="noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton(text="▶️", callback_data=f"page:{cat_index}:{page + 1}"))
    if nav:
        kb.row(*nav)
    kb.row(InlineKeyboardButton(text="⬅️ Категории", callback_data="catalog"))
    return kb.as_markup()


def item_detail_kb(item_id: int, cat_index: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🛒 В корзину", callback_data=f"add_cart:{item_id}"))
    kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cat:{cat_index}"))
    return kb.as_markup()


def cart_kb(has_items: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if has_items:
        kb.row(InlineKeyboardButton(text="✅ Оформить заказ", callback_data="checkout"))
        kb.row(InlineKeyboardButton(text="🏷 Промокод", callback_data="apply_promo"))
        kb.row(InlineKeyboardButton(text="🗑 Очистить", callback_data="clear_cart"))
    kb.row(InlineKeyboardButton(text="⬅️ На главную", callback_data="to_main"))
    return kb.as_markup()


def admin_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="➕ Добавить товар", callback_data="admin_add_item"))
    kb.row(InlineKeyboardButton(text="🗑 Удалить товар", callback_data="admin_del_item"))
    kb.row(InlineKeyboardButton(text="🏷 Добавить промокод", callback_data="admin_add_promo"))
    kb.row(InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"))
    kb.row(InlineKeyboardButton(text="🔄 Синхронизировать каталог", callback_data="admin_sync"))
    return kb.as_markup()
