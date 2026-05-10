import telebot
from telebot import types
import sqlite3

TOKEN = '8709726103:AAEqLzikyRxkusEyulxhvmL5sJ1Ivcb_THs'
ADMIN_ID =  6362382479 # Твой ID

bot = telebot.TeleBot(TOKEN)

def init_db():
    conn = sqlite3.connect('xiaomi_shop.db')
    cur = conn.cursor()
    # Таблица категорий и товаров
    cur.execute('CREATE TABLE IF NOT EXISTS cats (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)')
    cur.execute('CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, cat_id INTEGER, name TEXT, description TEXT, price INTEGER, photo_id TEXT)')
    # Таблица пользователей (кошелек)
    cur.execute('CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 0)')
    # Таблица промокодов
    cur.execute('CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, amount INTEGER, uses INTEGER DEFAULT 1)')
    # История активаций (чтобы не юзали дважды)
    cur.execute('CREATE TABLE IF NOT EXISTS promo_history (user_id INTEGER, code TEXT)')
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = sqlite3.connect('xiaomi_shop.db')
    res = conn.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if not res:
        conn.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
        conn.commit()
        return 0
    return res[0]

def main_menu(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📦 Каталог", "👤 Профиль")
    markup.add("🎟 Ввести промокод")
    if user_id == ADMIN_ID:
        markup.add("🛠 Админка")
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    init_db()
    get_balance(message.from_user.id) # Регаем юзера
    bot.send_message(message.chat.id, "Добро пожаловать!", reply_markup=main_menu(message.from_user.id))

# --- ПРОФИЛЬ И КОШЕЛЕК ---
@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(message):
    bal = get_balance(message.from_user.id)
    bot.send_message(message.chat.id, f"🆔 Твой ID: `{message.from_user.id}`\n💰 Баланс: **{bal} руб.**", parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🎟 Ввести промокод")
def promo_enter(message):
    msg = bot.send_message(message.chat.id, "Введите промокод:")
    bot.register_next_step_handler(msg, activate_promo)

def activate_promo(message):
    code = message.text.strip()
    u_id = message.from_user.id
    conn = sqlite3.connect('xiaomi_shop.db')
    cur = conn.cursor()
    
    # Проверка: юзал ли уже?
    history = cur.execute("SELECT * FROM promo_history WHERE user_id = ? AND code = ?", (u_id, code)).fetchone()
    if history:
        bot.send_message(message.chat.id, "❌ Вы уже активировали этот промокод!")
        return

    # Проверка: существует ли код?
    promo = cur.execute("SELECT amount, uses FROM promos WHERE code = ?", (code,)).fetchone()
    if promo and promo[1] > 0:
        amount = promo[0]
        cur.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, u_id))
        cur.execute("UPDATE promos SET uses = uses - 1 WHERE code = ?", (code,))
        cur.execute("INSERT INTO promo_history VALUES (?, ?)", (u_id, code))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ Успешно! Начислено {amount} руб.")
    else:
        bot.send_message(message.chat.id, "❌ Промокод не найден или закончился.")
    conn.close()

# --- АДМИНКА (ПРОМОКОДЫ) ---
@bot.callback_query_handler(func=lambda call: call.data == "make_promo")
def admin_promo(call):
    msg = bot.send_message(call.message.chat.id, "Введите данные промокода через пробел\n(Код Сумма Количество):\nНапр: `XIAOMI2025 500 10`")
    bot.register_next_step_handler(msg, save_promo)

def save_promo(message):
    try:
        code, amount, uses = message.text.split()
        conn = sqlite3.connect('xiaomi_shop.db')
        conn.execute("INSERT INTO promos (code, amount, uses) VALUES (?, ?, ?)", (code.upper(), int(amount), int(uses)))
        conn.commit()
        conn.close()
        bot.send_message(message.chat.id, f"✅ Промокод `{code.upper()}` на {amount} руб. создан!")
    except:
        bot.send_message(message.chat.id, "❌ Ошибка! Формат: КОД СУММА КОЛИЧЕСТВО")

# Добавь кнопку в admin_panel
@bot.message_handler(func=lambda m: m.text == "🛠 Админка" and m.from_user.id == ADMIN_ID)
def admin_panel(message):
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton("➕ Категория", callback_data="add_cat"),
        types.InlineKeyboardButton("📦 Добавить товар", callback_data="add_item"),
        types.InlineKeyboardButton("🎁 Создать промокод", callback_data="make_promo")
    )
    bot.send_message(message.chat.id, "Админ-панель:", reply_markup=markup)

# (Оставь остальные функции из прошлого кода: добавление товара, категорий и каталог)
