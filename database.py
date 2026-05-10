import aiosqlite

DB_NAME = "bot.db"


# =========================
# INIT DATABASE
# =========================
async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:

        # categories
        await db.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
        """)

        # products
        await db.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL DEFAULT 0,
            stock INTEGER DEFAULT 0,
            category TEXT
        )
        """)

        # cart
        await db.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOIN
