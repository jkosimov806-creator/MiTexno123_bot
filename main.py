import asyncio
import logging

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import TOKEN
from database import init_db, register_user
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


@dp.callback_query(F.data == "to_main")
async def back_to_main(c: types.CallbackQuery):
    await c.message.delete()
    name = c.from_user.first_name or "покупатель"
    await c.message.answer(
        f"◈ <b>MI TEXNO</b> 📱\nПривет, {name}! Выберите раздел:",
        reply_markup=main_kb(),
    )


async def main():
    init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
