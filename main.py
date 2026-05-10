from telegram.ext import Application, CommandHandler, CallbackQueryHandler

from handlers.start import start_handler
from handlers.menu import main_menu_handler
from handlers.catalog import get_catalog_handlers

TOKEN = "8709726103:AAEzNysfOYWb8hnWL44pUtSVAu_e0QLc38g"

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"))

    for h in get_catalog_handlers():
        app.add_handler(h)

    app.run_polling()

if __name__ == "__main__":
    main()
