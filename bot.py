import telebot
from telebot import types
import sqlite3

# --- sqlite3 ---
TOKEN = '8709726103:AAEqLzikyRxkusEyulxhvmL5sJ1Ivcb_THs'
ADMIN_ID = 123456789  # Твой ID цифрами (узнай у @userinfobot)

bot = telebot.TeleBot(TOKEN)

# --- РАБОТА С БАЗОЙ (ВНУТРИ ФАЙЛА) ---
def init_db():
    conn = sqlite3.connect('xiaomi_shop.db')
    cur = conn.cursor()
    cur.execute('CREATE TABLE IF NOT EXISTS cats (id INTEGER PRIMARY KEY, name TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY, cat_id INTEGER, name TEXT, price TEXT)')
    conn.commit()
    conn.close()

# --- ГЛАВНОЕ МЕНЮ ---
def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("📦 Каталог"))
    if user_id == ADMIN_ID:
        markup.add(types.KeyboardButton("🛠 Админка"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    init_db()
    bot.send_message(message.chat.id, "Добро пожаловать в магазин Xiaomi!", reply_markup=main_menu(message.from_user.id))

# --- АДМИНКА ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админка" and m.from_user.id == ADMIN_ID)
def admin_panel(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("➕ Добавить категорию", callback_data="add_cat"))
    markup.add(types.InlineKeyboardButton("🗑 Удалить категорию", callback_data="del_cat"))
    bot.send_message(message.chat.id, "Управление магазином:", reply_markup=markup)

# --- ДОБАВЛЕНИЕ КАТЕГОРИИ ---
@bot.callback_query_handler(func=lambda call: call.data == "add_cat")
def ask_cat_name(call):
    msg = bot.send_message(call.message.chat.id, "Введите название новой категории:")
    bot.register_next_step_handler(msg, save_category)

def save_category(message):
    conn = sqlite3.connect('xiaomi_shop.db')
    cur = conn.cursor()
    cur.execute("INSERT INTO cats (name) VALUES (?)", (message.text,))
    conn.commit()
    conn.close()
    bot.send_message(message.chat.id, f"✅ Категория '{message.text}' создана!")

# --- УДАЛЕНИЕ КАТЕГОРИИ ---
@bot.callback_query_handler(func=lambda call: call.data == "del_cat")
def list_cats_to_delete(call):
    conn = sqlite3.connect('xiaomi_shop.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM cats")
    cats = cur.fetchall()
    conn.close()

    if not cats:
        bot.send_message(call.message.chat.id, "Категорий пока нет.")
        return

    markup = types.InlineKeyboardMarkup()
    for cat in cats:
        markup.add(types.InlineKeyboardButton(f"❌ {cat[1]}", callback_data=f"drop_{cat[0]}"))
    bot.send_message(call.message.chat.id, "Выберите категорию для удаления:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("drop_"))
def confirm_delete(call):
    cat_id = call.data.split("_")[1]
    conn = sqlite3.connect('xiaomi_shop.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM cats WHERE id = ?", (cat_id,))
    conn.commit()
    conn.close()
    bot.answer_callback_query(call.id, "Удалено!")
    bot.edit_message_text("Категория удалена.", call.message.chat.id, call.message.message_id)

# --- КАТАЛОГ ДЛЯ ЮЗЕРА ---
@bot.message_handler(func=lambda m: m.text == "📦 Каталог")
def show_catalog(message):
    conn = sqlite3.connect('xiaomi_shop.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM cats")
    cats = cur.fetchall()
    conn.close()

    if not cats:
        bot.send_message(message.chat.id, "Магазин пока пуст.")
        return

    markup = types.InlineKeyboardMarkup()
    for cat in cats:
        markup.add(types.InlineKeyboardButton(cat[1], callback_data=f"view_{cat[0]}"))
    bot.send_message(message.chat.id, "Выберите раздел:", reply_markup=markup)

if __name__ == "__main__":
    print("Бот запущен...")
    bot.polling(none_stop=True)
