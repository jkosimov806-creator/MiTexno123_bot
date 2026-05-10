import telebot
from telebot import types
import sqlite3

# --- КОНФИГ (ЗАМЕНИ НА СВОИ ДАННЫЕ) ---
TOKEN = '8709726103:AAEqLzikyRxkusEyulxhvmL5sJ1Ivcb_THs'
ADMIN_ID = 6362382479  # Твой реальный ID (узнай у @userinfobot)

bot = telebot.TeleBot(TOKEN)

# --- БАЗА ДАННЫХ (ВНУТРИ ФАЙЛА) ---
def init_db():
    conn = sqlite3.connect('xiaomi_shop.db')
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS cats (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)')
    cur.execute('''CREATE TABLE IF NOT EXISTS items 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, cat_id INTEGER, name TEXT, 
                    description TEXT, price TEXT, photo_id TEXT)''')
    conn.commit()
    conn.close()

# --- ГЛАВНОЕ МЕНЮ ---
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📦 Каталог")
    if user_id == ADMIN_ID:
        markup.add("🛠 Админка")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    init_db()
    bot.send_message(message.chat.id, "Добро пожаловать в Xiaomi Shop!", reply_markup=main_menu(message.from_user.id))

# --- АДМИНКА (ГЛАВНОЕ) ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админка" and m.from_user.id == ADMIN_ID)
def admin_panel(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("➕ Добавить категорию", callback_data="add_cat"),
        types.InlineKeyboardButton("🗑 Удалить категорию", callback_data="del_cat"),
        types.InlineKeyboardButton("📦 Добавить товар", callback_data="add_item")
    )
    bot.send_message(message.chat.id, "Управление магазином:", reply_markup=markup)

# --- ДОБАВЛЕНИЕ КАТЕГОРИИ ---
@bot.callback_query_handler(func=lambda call: call.data == "add_cat")
def add_cat_start(call):
    msg = bot.send_message(call.message.chat.id, "Введите название категории:")
    bot.register_next_step_handler(msg, save_category)

def save_category(message):
    conn = sqlite3.connect('xiaomi_shop.db')
    conn.execute("INSERT INTO cats (name) VALUES (?)", (message.text,))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"✅ Категория '{message.text}' создана!")

# --- ДОБАВЛЕНИЕ ТОВАРА С ФОТО ---
@bot.callback_query_handler(func=lambda call: call.data == "add_item")
def add_item_start(call):
    conn = sqlite3.connect('xiaomi_shop.db')
    cats = conn.execute("SELECT * FROM cats").fetchall()
    conn.close()
    if not cats:
        bot.send_message(call.message.chat.id, "Сначала создайте категорию!")
        return
    markup = types.InlineKeyboardMarkup()
    for c in cats:
        markup.add(types.InlineKeyboardButton(c[1], callback_data=f"ai_{c[0]}"))
    bot.send_message(call.message.chat.id, "Выберите категорию для товара:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("ai_"))
def ask_photo(call):
    cat_id = call.data.split("_")[1]
    msg = bot.send_message(call.message.chat.id, "📸 Отправьте ФОТО товара:")
    bot.register_next_step_handler(msg, ask_desc, cat_id)

def ask_desc(message, cat_id):
    if not message.photo:
        bot.send_message(message.chat.id, "Это не фото. Начните заново.")
        return
    photo_id = message.photo[-1].file_id
    msg = bot.send_message(message.chat.id, "📝 Введите название и характеристики товара:")
    bot.register_next_step_handler(msg, ask_price, cat_id, photo_id)

def ask_price(message, cat_id, photo_id):
    desc = message.text
    msg = bot.send_message(message.chat.id, "💰 Введите цену (напр. 25000):")
    bot.register_next_step_handler(msg, save_item, cat_id, photo_id, desc)

def save_item(message, cat_id, photo_id, desc):
    price = message.text
    conn = sqlite3.connect('xiaomi_shop.db')
    conn.execute("INSERT INTO items (cat_id, description, price, photo_id) VALUES (?, ?, ?, ?)", 
                 (cat_id, desc, price, photo_id))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, "✅ Товар добавлен!")

# --- КАТАЛОГ С ЛИСТАЛКОЙ ---
@bot.message_handler(func=lambda m: m.text == "📦 Каталог")
def show_cats(message):
    conn = sqlite3.connect('xiaomi_shop.db')
    cats = conn.execute("SELECT * FROM cats").fetchall()
    conn.close()
    if not cats:
        bot.send_message(message.chat.id, "Каталог пуст.")
        return
    markup = types.InlineKeyboardMarkup()
    for c in cats:
        markup.add(types.InlineKeyboardButton(c[1], callback_data=f"vcat_{c[0]}_0"))
    bot.send_message(message.chat.id, "Выберите раздел:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("vcat_"))
def view_items(call):
    data = call.data.split("_")
    cat_id, index = int(data[1]), int(data[2])
    
    conn = sqlite3.connect('xiaomi_shop.db')
    items = conn.execute("SELECT * FROM items WHERE cat_id = ?", (cat_id,)).fetchall()
    conn.close()

    if not items:
        bot.answer_callback_query(call.id, "Здесь пока нет товаров.")
        return

    item = items[index]
    total = len(items)
    
    caption = f"🏷 Товар {index + 1}/{total}\n\n{item[3]}\n\n💰 Цена: {item[4]}"
    
    markup = types.InlineKeyboardMarkup(row_width=5)
    # Кнопки выбора номера
    btns = []
    for i in range(total):
        label = f"•{i+1}•" if i == index else str(i+1)
        btns.append(types.InlineKeyboardButton(label, callback_data=f"vcat_{cat_id}_{i}"))
    markup.add(*btns)
    
    # Назад / Вперед
    nav = []
    if index > 0:
        nav.append(types.InlineKeyboardButton("⬅️ Назад", callback_data=f"vcat_{cat_id}_{index-1}"))
    if index < total - 1:
        nav.append(types.InlineKeyboardButton("Вперед ➡️", callback_data=f"vcat_{cat_id}_{index+1}"))
    markup.add(*nav)
    markup.add(types.InlineKeyboardButton("🏠 В меню", callback_data="to_main"))

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except: pass
    bot.send_photo(call.message.chat.id, item[5], caption=caption, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "to_main")
def to_main(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    show_cats(call.message)

if __name__ == "__main__":
    init_db()
    bot.polling(none_stop=True)
