import asyncio
from aiogram import Bot, Dispatcher, types, F
from config import TOKEN
from database import init_db, db_query
from kb import main_kb
import support_h # Импортируем файл поддержки

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    db_query('INSERT OR IGNORE INTO users VALUES (?)', (message.from_user.id,))
    await message.answer("◈ **MI TEXNO** 📱\nВыберите раздел:", reply_markup=main_kb(message.from_user.id))

@dp.callback_query(F.data == "to_main")
async def back_to_main(c: types.CallbackQuery):
    await c.message.delete()
    await cmd_start(c.message)

async def main():
    init_db()
    dp.include_router(support_h.router) # Подключаем поддержку
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
