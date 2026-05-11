import asyncio
from aiogram import Bot, Dispatcher, types, F
from config import TOKEN, ADMIN_ID
import support_h # Импортируем наш новый файл
from kb import main_kb

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Подключаем роутер поддержки
dp.include_router(support_h.router)

@dp.message(F.text == "/start")
async def cmd_start(message: types.Message):
    await message.answer("◈ <b>MI TEXNO</b> 📱\nВыберите раздел:", 
                         reply_markup=main_kb(message.from_user.id, ADMIN_ID), 
                         parse_mode="HTML")

@dp.callback_query(F.data == "to_main")
async def back_home(c: types.CallbackQuery):
    await c.message.delete()
    await cmd_start(c.message)

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
