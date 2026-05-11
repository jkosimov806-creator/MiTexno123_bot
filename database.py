import sqlite3

def db_query(sql, params=(), fetch=False, fetch_one=False):
    with sqlite3.connect('mi_texno.db') as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        if fetch_one: return cursor.fetchone()
        if fetch: return cursor.fetchall()
        conn.commit()

def init_db():
    db_query('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)')
    # Создаем таблицу с полем categorie
    db_query('''CREATE TABLE IF NOT EXISTS items 
                (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                name TEXT, 
                price INTEGER, 
                desc TEXT, 
                photo TEXT, 
                categorie TEXT)''')
    db_query('CREATE TABLE IF NOT EXISTS promos (code TEXT PRIMARY KEY, discount INTEGER)')
