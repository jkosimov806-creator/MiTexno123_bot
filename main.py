import asyncio
import logging

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand

from config import TOKEN
from database import init_db, register_user, warm_cache
from kb import main_kb
import admin_h, support_h, catalog_h, cart_h

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s: %(message)s")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

dp.include_router(admin_h.router)
dp.include_router(support_h.router)
dp.include_router(catalog_h.router)
dp.include_router(cart_h.router)


@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    register_user(message.from_user.id)
    name = message.from_user.first_name or "покупатель"
    await message.answer(
        f"👋 Привет, <b>{name}</b>!\n\n◈ <b>MI TEXNO</b> 📱\nВыберите раздел:",
        reply_markup=main_kb(),
    )


@dp.message(F.text == "/catalog")
async def cmd_catalog(message: types.Message):
    from database import get_categories
    from kb import categories_kb
    cats = get_categories()
    if not cats:
        await message.answer("Каталог пока пуст 😔")
        return
    await message.answer(
        "<b>📋 КАТАЛОГ</b>\n━━━━━━━━━━━━━━━\nВыберите категорию:",
        reply_markup=categories_kb(cats),
    )


@dp.message(F.text == "/cart")
async def cmd_cart(message: types.Message):
    from database import cart_get
    from kb import cart_kb
    items = cart_get(message.from_user.id)
    if not items:
        await message.answer(
            "<b>🛒 Корзина пуста</b>\n\nДобавьте товары из каталога!",
            reply_markup=cart_kb(has_items=False),
        )
        return
    lines = ["<b>🛒 КОРЗИНА</b>\n━━━━━━━━━━━━━━━"]
    total = 0
    for row in items:
        lines.append(f"• {row['name']} × {row['qty']} = <b>{row['subtotal']} с.</b>")
        total += row["subtotal"]
    lines.append(f"━━━━━━━━━━━━━━━\n💰 Итого: <b>{total} с.</b>")
    await message.answer("\n".join(lines), reply_markup=cart_kb(has_items=True))


@dp.message(F.text == "/support")
async def cmd_support(message: types.Message):
    from config import SUPPORT_USERNAME
    from kb import back_main_kb
    await message.answer(
        f"🛡 <b>ПОДДЕРЖКА</b>\n━━━━━━━━━━━━━━━\n"
        f"Напишите нашему менеджеру:\n{SUPPORT_USERNAME}",
        reply_markup=back_main_kb(),
    )


@dp.callback_query(F.data == "to_main")
async def back_to_main(c: types.CallbackQuery):
    await c.message.delete()
    name = c.from_user.first_name or "покупатель"
    await c.message.answer(
        f"◈ <b>MI TEXNO</b> 📱\nПривет, {name}! Выберите раздел:",
        reply_markup=main_kb(),
    )


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="🏠 Главная"),
        BotCommand(command="catalog", description="📋 Каталог товаров"),
        BotCommand(command="cart", description="🛒 Корзина"),
        BotCommand(command="support", description="🛡 Поддержка"),
    ]
    await bot.set_my_commands(commands)


async def main():
    init_db()
    warm_cache()  # загружаем все товары в память при старте
    await bot.delete_webhook(drop_pending_updates=True)
    await set_commands(bot)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
