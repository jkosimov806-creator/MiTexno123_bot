from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
)

from handlers.start import start_handler
from handlers.menu import main_menu_handler
from handlers.catalog import get_catalog_handlers

TOKEN = "YOUR_BOT_TOKEN"


def main():
    app = Application.builder().token(TOKEN).build()

    # =====================
    # COMMANDS
    # =====================
    app.add_handler(CommandHandler("start", start_handler))

    # =====================
    # MENU
    # =====================
    app.add_handler(
        CallbackQueryHandler(main_menu_handler, pattern="^main_menu$")
    )

    # =====================
    # CATALOG (ВАЖНО)
    # =====================
    handlers =
