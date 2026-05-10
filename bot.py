import telebot
from telebot import types
import sqlite3

TOKEN = '8709726103:AAEqLzikyRxkusEyulxhvmL5sJ1Ivcb_THs'
ADMIN_ID = 6362382479  # ТВОЙ ID

bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect('xiaomi_shop.db')
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS cats (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)')
    cur.execute('''CREATE TABLE IF NOT EXISTS items 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, cat_id INTEGER, name TEXT, 
                    description TEXT, price TEXT, photo_id TEXT)''')
    conn.commit()
    conn.close()

# --- АДМИНКА: ДОБАВЛЕНИЕ ТОВАРА С ФОТО ---
@bot.callback_query_handler(func=lambda call: call.data == "add_item")
def admin_add_item(call):
    conn = sqlite3.connect('xiaomi_shop.db')
    cats = conn.execute("SELECT * FROM cats").fetchall()
    conn.close()
    if not cats:
        bot.send_message(call.message.chat.id, "❌ Сначала создай категорию!")
        return
    markup = types.InlineKeyboardMarkup()
    for c in cats:
        markup.add(types.InlineKeyboardButton(c[1], callback_data=f"ai_{c[0]}"))
    bot.send_message(call.message.chat.id, "Выбери категорию для товара:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ai_"))
def add_item_photo(call):
    cat_id = call.data.split("_")[1]
    msg = bot.send_message(call.message.chat.id, "🖼 Отправь ФОТО товара (как картинку):")
    bot.register_next_step_handler(msg, add_item_desc, cat_id)

def add_item_desc(message, cat_id):
    if not message.photo:
        bot.send_message(message.chat.id, "❌ Это не фото. Нажми 'Добавить товар' заново.")
        return
    photo_id = message.photo[-1].file_id # Берем лучшее качество
    msg = bot.send_message(message.chat.id, "📝 Введи название и описание (характеристики):")
    bot.register_next_step_handler(msg, add_item_price, cat_id, photo_id)

def add_item_price(message, cat_id, photo_id):
    description = message.text
    msg = bot.send_message(message.chat.id, "💰 Введи цену товара (например: 15.000 руб):")
    bot.register_next_step_handler(msg, save_all, cat_id, photo_id, description)

def save_all(message, cat_id, photo_id, description):
    price = message.text
    conn = sqlite3.connect('xiaomi_shop.db')
    conn.execute("INSERT INTO items (cat_id, description, price, photo_id) VALUES (?, ?, ?, ?)", 
                 (cat_id, description, price, photo_id))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "✅ Товар успешно добавлен с фото!")

# --- КАТАЛОГ С ЛИСТАЛКОЙ ---
@bot.callback_query_handler(func=lambda call: call.data.startswith("view_"))
def show_items(call):
    data = call.data.split("_")
    cat_id = int(data[1])
    index = int(data[2]) if len(data) > 2 else 0

    conn = sqlite3.connect('xiaomi_shop.db')
    items = conn.execute("SELECT * FROM items WHERE cat_id = ?", (cat_id,)).fetchall()
    conn.close()

    if not items:
        bot.answer_callback_query(call.id, "В этой категории пока нет товаров")
        return

    item = items[index]
    total = len(items)
    
    # Текст под фото
    text = f"📦 **Товар {index + 1} из {total}**\n\n{item[3]}\n\n💰 **Цена:** {item[4]}"

    markup = types.InlineKeyboardMarkup(row_width=5)
    
    # Кнопки с цифрами 1 2 3...
    btns = []
    for i in range(total):
        label = f"·{i+1}·" if i == index else str(i+1)
        btns.append(types.InlineKeyboardButton(label, callback_data=f"view_{cat_id}_{i}"))
    markup.add(*btns)

    # Стрелочки Назад / Вперед
    nav = []
    if index > 0:
        nav.append(types.InlineKeyboardButton("🔙 Назад", callback_data=f"view_{cat_id}_{index-1}"))
    if index < total - 1:
        nav.append(types.InlineKeyboardButton("Вперед 🔜", callback_data=f"view_{cat_id}_{index+1}"))
    markup.add(*nav)
    
    markup.add(types.InlineKeyboardButton("🏠 К категориям", callback_data="to_cats"))

    # Обновляем сообщение (удаляем старое, шлем новое с фото)
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass

    bot.send_photo(call.message.chat.id, item[5], caption=text, reply_markup=markup, parse_mode="Markdown")

# --- ОСТАЛЬНАЯ ЛОГИКА (ГЛАВНОЕ МЕНЮ И Т.Д.) ---
@bot.message_handler(func=lambda m: m.text == "📦 Каталог")
def catalog(message):
    conn = sqlite3.connect('xiaomi_shop.db')
    cats = conn.execute("SELECT * FROM cats").fetchall()
    conn.close()
    markup = types.InlineKeyboardMarkup()
    for c in cats:
        markup.add(types.InlineKeyboardButton(c[1], callback_data=f"view_{c[0]}_0"))
    bot.send_message(message.chat.id, "Выберите категорию:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "to_cats")
def back(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    catalog(call.message)

@bot.message_handler(func=lambda m: m.text == "🛠 Админка" and m.from_user.id == ADMIN_ID)
def admin(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ Категория", callback_data="add_cat"))
    markup.add(types.InlineKeyboardButton("📦 Добавить товар", callback_data="add_item"))
    bot.send_message(message.chat.id, "Панель управления:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "add_cat")
def add_cat(call):
    msg = bot.send_message(call.message.chat.id, "Название новой категории:")
    bot.register_next_step_handler(msg, save_cat)

def save_cat(message):
    conn = sqlite3.connect('xiaomi_shop.db')
    conn.execute("INSERT INTO cats (name) VALUES (?)", (message.text,))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "✅ Категория добавлена!")

if __name__ == "__main__":
    init_db()
    bot.polling(none_stop=True)
