from aiogram import Router, F, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from database import cart_get, cart_clear, cart_remove, get_promo, reduce_stock, save_pending_order, get_pending_order, delete_pending_order
from kb import cart_kb

router = Router()

REQUISITES_NUMBER = "+992 92-866-35-10"

BANKS = {
    "eskhata": ("🟦 Эсхата", "Эсхата"),
    "dushanbe": ("🟨 Dushanbe City", "Dushanbe City"),
    "alif": ("💳 Alif Bank", "Alif Bank"),
}


class CartState(StatesGroup):
    promo = State()
    bank = State()
    address = State()
    phone = State()


def _cart_text(items, discount: int = 0) -> tuple[str, int]:
    lines = ["<b>🛒 КОРЗИНА</b>\n━━━━━━━━━━━━━━━"]
    total = 0
    for row in items:
        lines.append(f"• {row['name']} × {row['qty']} = <b>{row['subtotal']} с.</b>")
        total += row["subtotal"]
    lines.append("━━━━━━━━━━━━━━━")
    if discount:
        final = int(total * (1 - discount / 100))
        lines.append(f"🏷 Скидка: {discount}%")
        lines.append(f"💰 Итого: <s>{total} с.</s> → <b>{final} с.</b>")
        total = final
    else:
        lines.append(f"💰 Итого: <b>{total} с.</b>")
    return "\n".join(lines), total


def banks_kb() -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, (label, _) in BANKS.items():
        kb.row(InlineKeyboardButton(text=label, callback_data=f"bank:{key}"))
    kb.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="view_cart"))
    return kb.as_markup()


def order_confirm_kb(user_id: int) -> types.InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"order_confirm:{user_id}"),
        InlineKeyboardButton(text="❌ Отменить", callback_data=f"order_cancel:{user_id}"),
    )
    return kb.as_markup()


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


# ─── Оформление заказа ────────────────────────────────────────────────────────

@router.callback_query(F.data == "checkout")
async def checkout(c: types.CallbackQuery, state: FSMContext):
    items = cart_get(c.from_user.id)
    if not items:
        await c.answer("Корзина пуста!", show_alert=True)
        return
    await c.message.edit_text(
        "💳 <b>Выберите способ оплаты:</b>\n━━━━━━━━━━━━━━━\n"
        "После выбора банка вам будут показаны реквизиты для оплаты.",
        reply_markup=banks_kb(),
        parse_mode="HTML",
    )


@router.callback_query(F.data.startswith("bank:"))
async def choose_bank(c: types.CallbackQuery, state: FSMContext):
    bank_key = c.data.split(":")[1]
    bank_label, bank_name = BANKS.get(bank_key, ("", ""))
    await state.update_data(bank=bank_name)

    await c.message.edit_text(
        f"{bank_label} <b>{bank_name}</b>\n━━━━━━━━━━━━━━━\n"
        f"📱 Номер для перевода:\n"
        f"<code>{REQUISITES_NUMBER}</code>\n\n"
        f"После оплаты заполните форму заказа.\n\n"
        f"📍 Введите ваш <b>адрес доставки:</b>",
        parse_mode="HTML",
    )
    await state.set_state(CartState.address)


@router.message(CartState.address)
async def get_address(m: types.Message, state: FSMContext):
    await state.update_data(address=m.text.strip())
    await m.answer(
        "📞 Введите ваш <b>номер телефона</b>:\n"
        "Формат: <code>+992XXXXXXXXX</code>",
        parse_mode="HTML",
    )
    await state.set_state(CartState.phone)


@router.message(CartState.phone)
async def get_phone(m: types.Message, state: FSMContext):
    phone = m.text.strip().replace(" ", "").replace("-", "")

    # проверка формата +992XXXXXXXXX
    if not (phone.startswith("+992") and len(phone) == 13 and phone[1:].isdigit()):
        await m.answer(
            "❌ Неверный формат номера!\n"
            "Введите в формате: <code>+992XXXXXXXXX</code>",
            parse_mode="HTML",
        )
        return

    data = await state.get_data()
    await state.update_data(phone=phone)

    items = cart_get(m.from_user.id)
    _, total = _cart_text(items, data.get("promo_discount", 0))

    order_lines = "\n".join(
        f"  • {r['name']} × {r['qty']} = {r['subtotal']} с." for r in items
    )

    # показываем итог заказа клиенту
    await m.answer(
        f"📋 <b>Ваш заказ:</b>\n━━━━━━━━━━━━━━━\n"
        f"{order_lines}\n━━━━━━━━━━━━━━━\n"
        f"💰 Итого: <b>{total} с.</b>\n"
        f"💳 Оплата: {data.get('bank', '—')}\n"
        f"📍 Адрес: {data.get('address', '—')}\n"
        f"📞 Телефон: {phone}\n\n"
        f"⏳ Ожидайте подтверждения от менеджера.",
        parse_mode="HTML",
    )

    # отправляем заказ админу
    import json
    order_data = [(r['id'], r['qty']) for r in items]
    save_pending_order(m.from_user.id, json.dumps(order_data), total)

    from config import ADMIN_ID
    user = m.from_user
    username = f"@{user.username}" if user.username else f"ID: {user.id}"

    try:
        await m.bot.send_message(
            ADMIN_ID,
            f"🔔 <b>Новый заказ!</b>\n"
            f"👤 {user.first_name} | {username}\n"
            f"📞 {phone}\n"
            f"📍 {data.get('address', '—')}\n"
            f"💳 Оплата: {data.get('bank', '—')}\n"
            f"━━━━━━━━━━━━━━━\n{order_lines}\n━━━━━━━━━━━━━━━\n"
            f"💰 Итого: <b>{total} с.</b>",
            parse_mode="HTML",
            reply_markup=order_confirm_kb(m.from_user.id),
        )
    except Exception:
        pass

    cart_clear(m.from_user.id)
    await state.update_data(promo_discount=0)
    await state.clear()


# ─── Подтверждение заказа админом ─────────────────────────────────────────────

@router.callback_query(F.data.startswith("order_confirm:"))
async def order_confirm(c: types.CallbackQuery):
    user_id = int(c.data.split(":")[1])
    import json

    order = get_pending_order(user_id)
    if not order:
        await c.answer("Заказ не найден или уже обработан", show_alert=True)
        return

    items = json.loads(order["items"])
    for item_id, qty in items:
        reduce_stock(item_id, qty)

    delete_pending_order(user_id)

    try:
        await c.bot.send_message(
            user_id,
            "✅ <b>Ваш заказ подтверждён!</b>\n"
            "Менеджер свяжется с вами в ближайшее время.",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await c.message.edit_text(
        c.message.text + "\n\n✅ <b>Заказ подтверждён</b>",
        parse_mode="HTML",
    )
    await c.answer("✅ Заказ подтверждён, остатки обновлены!")


@router.callback_query(F.data.startswith("order_cancel:"))
async def order_cancel(c: types.CallbackQuery):
    user_id = int(c.data.split(":")[1])
    delete_pending_order(user_id)

    try:
        await c.bot.send_message(
            user_id,
            "❌ <b>Ваш заказ отменён.</b>\n"
            "Свяжитесь с менеджером для уточнения.",
            parse_mode="HTML",
        )
    except Exception:
        pass

    await c.message.edit_text(
        c.message.text + "\n\n❌ <b>Заказ отменён</b>",
        parse_mode="HTML",
    )
    await c.answer("Заказ отменён")
