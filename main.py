import asyncio
import logging

from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import TOKEN
from database import init_db, register_user
from keyboards import main_kb
from handlers import admin, catalog, cart, support

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def create_bot() -> Bot:
    return Bot(
        token=TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(admin.router)
    dp.include_router(support.router)
    dp.include_router(catalog.router)
    dp.include_router(cart.router)
    return dp


async def on_start(message: types.Message):
    register_user(message.from_user.id)
    name = message.from_user.first_name or "покупатель"
    await message.answer(
        f"👋 Привет, <b>{name}</b>!\n\n"
        "◈ Добро пожаловать в <b>MI TEXNO</b> 📱\n"
        "Выберите раздел:",
        reply_markup=main_kb(),
    )


async def on_back_to_main(c: types.CallbackQuery):
    await c.message.delete()
    register_user(c.from_user.id)
    name = c.from_user.first_name or "покупатель"
    await c.message.answer(
        f"◈ <b>MI TEXNO</b> 📱\n"
        f"Привет, {name}! Выберите раздел:",
        reply_markup=main_kb(),
    )


async def main():
    init_db()
    logger.info("Database initialized")

    bot = create_bot()
    dp = create_dispatcher()

    dp.message.register(on_start, F.text == "/start")
    dp.callback_query.register(on_back_to_main, F.data == "to_main")

    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot started")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
