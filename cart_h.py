from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database import cart_get, cart_clear, cart_remove, get_promo
from kb import cart_kb

router = Router()


class CartState(StatesGroup):
    promo = State()


def _cart_text(items, discount: int = 0) -> tuple[str, int]:
    lines = ["<b>🛒 КОРЗИНА</b>\n━━━━━━━━━━━━━━━"]
    total = 0
    for row in items:
        lines.append(f"• {row['name']} × {row['qty']} = <b>{row['subtotal']} Сомони</b>")
        total += row["subtotal"]
    lines.append("━━━━━━━━━━━━━━━")
    if discount:
        final = int(total * (1 - discount / 100))
        lines.append(f"🏷 Скидка: {discount}%")
        lines.append(f"💰 Итого: <s>{total} ₽</s> → <b>{final} Сомони</b>")
        total = final
    else:
        lines.append(f"💰 Итого: <b>{total} Сомони</b>")
    return "\n".join(lines), total


@router.callback_query(F.data == "view_cart")
async def view_cart(c: types.CallbackQuery, state: FSMContext):
    items = cart_get(c.from_user.id)
    if not items:
        await c.message.edit_text(
            "<b>🛒 Корзина пуста</b>\n\nДобавьте товары из каталога!",
            reply_markup=cart_kb(has_items=False), parse_mode="HTML",
        )
        return
    data = await state.get_data()
    text, _ = _cart_text(items, data.get("promo_discount", 0))
    await c.message.edit_text(text, reply_markup=cart_kb(has_items=True), parse_mode="HTML")


@router.callback_query(F.data == "clear_cart")
async def clear_cart(c: types.CallbackQuery, state: FSMContext):
    cart_clear(c.from_user.id)
    await state.update_data(promo_discount=0)
    await c.answer("🗑 Корзина очищена")
    await c.message.edit_text(
        "<b>🛒 Корзина пуста</b>",
        reply_markup=cart_kb(has_items=False), parse_mode="HTML",
    )


@router.callback_query(F.data == "apply_promo")
async def ask_promo(c: types.CallbackQuery, state: FSMContext):
    await c.message.answer("🏷 Введите промокод:")
    await state.set_state(CartState.promo)


@router.message(CartState.promo)
async def handle_promo(m: types.Message, state: FSMContext):
    promo = get_promo(m.text.strip().upper())
    if not promo:
        await m.answer("❌ Промокод недействителен.")
        await state.clear()
        return
    discount = promo["discount"]
    await state.update_data(promo_discount=discount)
    await state.clear()
    await m.answer(f"✅ Промокод применён! Скидка: <b>{discount}%</b>", parse_mode="HTML")
    items = cart_get(m.from_user.id)
    text, _ = _cart_text(items, discount)
    await m.answer(text, reply_markup=cart_kb(has_items=True), parse_mode="HTML")


@router.callback_query(F.data == "checkout")
async def checkout(c: types.CallbackQuery, state: FSMContext):
    items = cart_get(c.from_user.id)
    if not items:
        await c.answer("Корзина пуста!", show_alert=True)
        return
    data = await state.get_data()
    _, total = _cart_text(items, data.get("promo_discount", 0))

    order_lines = "\n".join(f"  • {r['name']} × {r['qty']} = {r['subtotal']} Сомони" for r in items)
    from config import ADMIN_ID
    try:
        await c.bot.send_message(
            ADMIN_ID,
            f"🔔 <b>Новый заказ!</b>\n"
            f"👤 ID: <code>{c.from_user.id}</code> | @{c.from_user.username or '—'}\n"
            f"━━━━━━━━━━━━━━━\n{order_lines}\n━━━━━━━━━━━━━━━\n"
            f"💰 Итого: <b>{total} ₽</b>",
            parse_mode="HTML",
        )
    except Exception:
        pass

    cart_clear(c.from_user.id)
    await state.update_data(promo_discount=0)
    await c.message.edit_text(
        "✅ <b>Заказ оформлен!</b>\nМенеджер свяжется с вами в ближайшее время.",
        reply_markup=cart_kb(has_items=False), parse_mode="HTML",
    )
