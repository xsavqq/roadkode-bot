import aiosqlite
from datetime import datetime
from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    full_name   TEXT,
    phone       TEXT,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS cart_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    link        TEXT,
    photo_id    TEXT,
    price_yuan  REAL NOT NULL,
    quantity    INTEGER NOT NULL,
    size        TEXT,
    cost_rub    REAL NOT NULL,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    status      TEXT NOT NULL DEFAULT 'Новая',
    total_rub   REAL NOT NULL,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id    INTEGER NOT NULL,
    link        TEXT,
    photo_id    TEXT,
    price_yuan  REAL NOT NULL,
    quantity    INTEGER NOT NULL,
    size        TEXT,
    cost_rub    REAL NOT NULL
);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()


async def ensure_user(user_id: int, username: str, full_name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if row is None:
            await db.execute(
                "INSERT INTO users (user_id, username, full_name, phone, created_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, username, full_name, None, datetime.utcnow().isoformat()),
            )
            await db.commit()


async def set_phone(user_id: int, phone: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET phone = ? WHERE user_id = ?", (phone, user_id))
        await db.commit()


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return await cur.fetchone()


async def add_cart_item(user_id: int, link: str, photo_id: str, price_yuan: float,
                         quantity: int, size: str, cost_rub: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO cart_items (user_id, link, photo_id, price_yuan, quantity, size, cost_rub, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, link, photo_id, price_yuan, quantity, size, cost_rub, datetime.utcnow().isoformat()),
        )
        await db.commit()


async def get_cart(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM cart_items WHERE user_id = ? ORDER BY id", (user_id,)
        )
        return await cur.fetchall()


async def get_cart_total(user_id: int) -> float:
    items = await get_cart(user_id)
    return round(sum(i["cost_rub"] for i in items), 2)


async def delete_cart_item(item_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM cart_items WHERE id = ? AND user_id = ?", (item_id, user_id))
        await db.commit()


async def clear_cart(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM cart_items WHERE user_id = ?", (user_id,))
        await db.commit()


async def get_cart_item(item_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM cart_items WHERE id = ? AND user_id = ?", (item_id, user_id)
        )
        return await cur.fetchone()


async def create_order_from_cart(user_id: int) -> int | None:
    items = await get_cart(user_id)
    if not items:
        return None
    total = round(sum(i["cost_rub"] for i in items), 2)
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO orders (user_id, status, total_rub, created_at) VALUES (?, ?, ?, ?)",
            (user_id, "Новая", total, datetime.utcnow().isoformat()),
        )
        order_id = cur.lastrowid
        for i in items:
            await db.execute(
                """INSERT INTO order_items (order_id, link, photo_id, price_yuan, quantity, size, cost_rub)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (order_id, i["link"], i["photo_id"], i["price_yuan"], i["quantity"], i["size"], i["cost_rub"]),
            )
        await db.commit()
    await clear_cart(user_id)
    return order_id


async def get_order_items(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM order_items WHERE order_id = ?", (order_id,))
        return await cur.fetchall()


async def get_user_orders(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC", (user_id,)
        )
        return await cur.fetchall()


async def get_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        return await cur.fetchone()


async def set_order_status(order_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
        await db.commit()
