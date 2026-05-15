import sqlite3
from contextlib import contextmanager

DB_PATH = "/data/mi_texno.db"

# ─── Кэш в памяти ─────────────────────────────────────────────────────────────
_cache_categories: list[str] = []
_cache_items: dict[str, list] = {}


def warm_cache():
    global _cache_categories, _cache_items
    rows = db_query("SELECT DISTINCT category FROM items WHERE category != ''", fetch=True)
    _cache_categories = [r[0] for r in rows] if rows else []
    _cache_items = {}
    for cat in _cache_categories:
        _cache_items[cat] = db_query("SELECT * FROM items WHERE category = ?", (cat,), fetch=True) or []


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def db_query(sql: str, params: tuple = (), *, fetch=False, fetch_one=False):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        if fetch_one:
            return cur.fetchone()
        if fetch:
            return cur.fetchall()


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id     INTEGER PRIMARY KEY,
                joined TEXT DEFAULT (datetime('now'))
            );
            CREATE TABLE IF NOT EXISTS items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                price       INTEGER NOT NULL,
                description TEXT    DEFAULT '',
                photo       TEXT    DEFAULT '',
                category    TEXT    DEFAULT '',
                stock       INTEGER DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS cart (
                user_id INTEGER NOT NULL,
                item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
                qty     INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (user_id, item_id)
            );
            CREATE TABLE IF NOT EXISTS promos (
                code     TEXT    PRIMARY KEY,
                discount INTEGER NOT NULL CHECK(discount BETWEEN 1 AND 100),
                active   INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS pending_orders (
                user_id INTEGER PRIMARY KEY,
                items   TEXT    NOT NULL,
                total   INTEGER NOT NULL,
                created TEXT    DEFAULT (datetime('now'))
            );
        """)


# ─── Users ────────────────────────────────────────────────────────────────────

def register_user(user_id: int):
    db_query("INSERT OR IGNORE INTO users (id) VALUES (?)", (user_id,))


def get_all_user_ids() -> list[int]:
    rows = db_query("SELECT id FROM users", fetch=True)
    return [r[0] for r in rows] if rows else []


# ─── Items ────────────────────────────────────────────────────────────────────

def add_item(name: str, price: int, description: str, category: str, photo: str):
    db_query(
        "INSERT INTO items (name, price, description, category, photo) VALUES (?,?,?,?,?)",
        (name, price, description, category, photo),
    )
    warm_cache()


def get_categories() -> list[str]:
    return _cache_categories


def get_items_by_category(category: str):
    return _cache_items.get(category, [])


def get_item(item_id: int):
    return db_query("SELECT * FROM items WHERE id = ?", (item_id,), fetch_one=True)


def delete_item(item_id: int):
    db_query("DELETE FROM items WHERE id = ?", (item_id,))
    warm_cache()


def reduce_stock(item_id: int, qty: int):
    db_query(
        "UPDATE items SET stock = MAX(0, stock - ?) WHERE id = ?",
        (qty, item_id),
    )
    warm_cache()


# ─── Синхронизация из Google Sheets ──────────────────────────────────────────

def sync_items_from_sheet(rows: list) -> int:
    valid = []
    for row in rows:
        name = str(row.get("name", "")).strip()
        price = str(row.get("price", "0")).strip()
        description = str(row.get("description", "")).strip()
        category = str(row.get("category", "")).strip()
        photo = str(row.get("photo", "")).strip()
        stock = str(row.get("stock", "0")).strip()
        if not name:
            continue
        if not price.isdigit():
            price = "0"
        if not stock.isdigit():
            stock = "0"
        valid.append((name, int(price), description, category, photo, int(stock)))

    with get_conn() as conn:
        conn.execute("DELETE FROM items")
        conn.executemany(
            "INSERT INTO items (name, price, description, category, photo, stock) VALUES (?,?,?,?,?,?)",
            valid,
        )

    warm_cache()
    return len(valid)


# ─── Cart ─────────────────────────────────────────────────────────────────────

def cart_add(user_id: int, item_id: int):
    db_query(
        "INSERT INTO cart (user_id, item_id, qty) VALUES (?,?,1) "
        "ON CONFLICT(user_id, item_id) DO UPDATE SET qty = qty + 1",
        (user_id, item_id),
    )


def cart_remove(user_id: int, item_id: int):
    db_query("DELETE FROM cart WHERE user_id = ? AND item_id = ?", (user_id, item_id))


def cart_clear(user_id: int):
    db_query("DELETE FROM cart WHERE user_id = ?", (user_id,))


def cart_get(user_id: int):
    return db_query(
        """SELECT i.id, i.name, i.price, c.qty, i.price * c.qty AS subtotal
           FROM cart c JOIN items i ON i.id = c.item_id
           WHERE c.user_id = ?""",
        (user_id,), fetch=True,
    ) or []


# ─── Pending Orders ───────────────────────────────────────────────────────────

def save_pending_order(user_id: int, items_json: str, total: int):
    db_query(
        "INSERT OR REPLACE INTO pending_orders (user_id, items, total) VALUES (?,?,?)",
        (user_id, items_json, total),
    )


def get_pending_order(user_id: int):
    return db_query(
        "SELECT * FROM pending_orders WHERE user_id = ?", (user_id,), fetch_one=True
    )


def delete_pending_order(user_id: int):
    db_query("DELETE FROM pending_orders WHERE user_id = ?", (user_id,))


# ─── Promos ───────────────────────────────────────────────────────────────────

def get_promo(code: str):
    return db_query(
        "SELECT * FROM promos WHERE code = ? AND active = 1", (code,), fetch_one=True
    )


def add_promo(code: str, discount: int):
    db_query(
        "INSERT OR REPLACE INTO promos (code, discount, active) VALUES (?,?,1)",
        (code, discount),
    )
