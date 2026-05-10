import asyncio 
import logging
import os

import telegram.error
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from database import init_db
from handlers.start import start_handler, menu_handler
from handlers.catalog import get_catalog_handlers
from handlers.cart import show_cart_handler, remove_from_cart_handler, show_orders_handler
from handlers.checkout import checkout_conv_handler
from handlers.admin import admin_conv_handler
from handlers.payment import get_payment_handlers
from handlers.wallet import wallet_conv_handler, wallet_standalone_handlers

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)

async def post_init(application):
    await init_db()
    await application.bot.delete_webhook(drop_pending_updates=True)
    for attempt in range(15):
        try:
            await application.bot.get_updates(offset=-1, timeout=0)
            logging.info("Session ready.")
            break
        except telegram.error.Conflict:
            await asyncio.sleep(4)
        except Exception:
            break

def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN is not set.")

    app = Application.builder().token(token).post_init(post_init).build()

    app.add_handler(admin_conv_handler())
    app.add_handler(checkout_conv_handler())
    app.add_handler(wallet_conv_handler())

    for h in get_catalog_handlers(): app.add_handler(h)
    for h in get_payment_handlers(): app.add_handler(h)
    for h in wallet_standalone_handlers(): app.add_handler(h)

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(menu_handler, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(show_cart_handler, pattern="^show_cart$"))
    app.add_handler(CallbackQueryHandler(remove_from_cart_handler, pattern="^remove_cart_\\d+$"))
    app.add_handler(CallbackQueryHandler(show_orders_handler, pattern="^show_orders$"))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
