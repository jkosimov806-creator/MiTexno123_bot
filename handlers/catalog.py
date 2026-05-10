from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import database
from utils import safe_edit_text

async def show_catalog_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает список категорий"""
    query = update.callback_query
    await query.answer()

    categories = await database.get_categories()
    if not categories:
        await safe_edit_text(query, "📦 Категории пока не добавлены.")
        return

    keyboard = []
    for cat in categories:
        # При клике на категорию открываем первый товар (индекс 0)
        keyboard.append([InlineKeyboardButton(cat, callback_data=f"cat_{cat}_0")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Главное меню", callback_data="main_menu")])

    await safe_edit_text(
        query,
        "📂 *Выберите категорию товаров:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_category_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает один товар из категории с кнопками переключения"""
    query = update.callback_query
    await query.answer()

    # Разбираем callback: cat_НазваниеКатегории_ИндексТовара
    data = query.data.split("_")
    category_name = data[1]
    current_index = int(data[2])

    products = await database.get_products_by_category(category_name)

    if not products:
        await safe_edit_text(query, "В этой категории пока нет товаров.", 
                             reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Назад", callback_data="show_catalog")]]))
        return

    # Проверка индекса (на случай, если товары удалили)
    if current_index >= len(products):
        current_index = 0
    elif current_index < 0:
        current_index = len(products) - 1

    product = products[current_index]
    total_count = len(products)

    # Формируем описание товара
    text = (
        f"🏷 *{product['name']}*\n\n"
        f"📝 {product['description']}\n\n"
        f"💰 Цена: *{product['price']:.2f} сомонӣ*\n"
        f"📦 В наличии: {product['stock']} шт.\n\n"
        f"📍 Категория: #{category_name}"
    )

    # Кнопки навигации (листалка)
    nav_row = []
    # Если товаров больше одного, рисуем стрелки
    if total_count > 1:
        prev_idx = current_index - 1 if current_index > 0 else total_count - 1
        next_idx = current_index + 1 if current_index < total_count - 1 else 0
        
        nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"cat_{category_name}_{prev_idx}"))
        nav_row.append(InlineKeyboardButton(f"{current_index + 1} / {total_count}", callback_data="ignore"))
        nav_row.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"cat_{category_name}_{next_idx}"))

    keyboard = []
    if nav_row:
        keyboard.append(nav_row)
    
    keyboard.append([InlineKeyboardButton("🛒 Добавить в корзину", callback_data=f"buy_{product['id']}")])
    keyboard.append([InlineKeyboardButton("📂 К категориям", callback_data="show_catalog")])
    keyboard.append([InlineKeyboardButton("🏠 В меню", callback_data="main_menu")])

    # Если у товара есть фото (путь к файлу или file_id), можно добавить логику с фото. 
    # Но пока делаем надежный текстовый вариант.
    await safe_edit_text(
        query,
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def add_to_cart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Добавление товара в корзину"""
    query = update.callback_query
    product_id = int(query.data.split("_")[1])
    user_id = query.from_user.id

    # Логика добавления в БД
    await database.add_to_cart(user_id, product_id, 1)
    
    # Показываем уведомление (всплывающее окно сверху)
    await query.answer("✅ Товар добавлен в корзину!", show_alert=False)

def get_catalog_handlers():
    """Список хендлеров для регистрации в main.py"""
    from telegram.ext import CallbackQueryHandler
    return [
        CallbackQueryHandler(show_catalog_handler, pattern="^show_catalog$"),
        CallbackQueryHandler(show_category_products, pattern="^cat_"),
        CallbackQueryHandler(add_to_cart_handler, pattern="^buy_"),
    ]
