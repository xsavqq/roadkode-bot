import random

import aiosqlite
from datetime import datetime
from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    full_name   TEXT,
    phone       TEXT,
    client_code TEXT,
    referred_by INTEGER,
    balance_rub REAL DEFAULT 0,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS cart_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id       INTEGER NOT NULL,
    link          TEXT,
    photo_id      TEXT,
    price_yuan    REAL NOT NULL,
    quantity      INTEGER NOT NULL,
    size          TEXT,
    weight_kg     REAL,
    weight_min_kg REAL,
    weight_max_kg REAL,
    weight_estimated INTEGER DEFAULT 0,
    shipping_rub  REAL DEFAULT 0,
    cost_rub      REAL NOT NULL,
    created_at    TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    status      TEXT NOT NULL DEFAULT 'Новая',
    total_rub   REAL NOT NULL,
    weight_kg   REAL,
    weight_set  INTEGER DEFAULT 0,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id      INTEGER NOT NULL,
    link          TEXT,
    photo_id      TEXT,
    price_yuan    REAL NOT NULL,
    quantity      INTEGER NOT NULL,
    size          TEXT,
    weight_kg     REAL,
    weight_min_kg REAL,
    weight_max_kg REAL,
    weight_estimated INTEGER DEFAULT 0,
    shipping_rub  REAL DEFAULT 0,
    cost_rub      REAL NOT NULL
);
"""


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        # Миграция для уже существующей SQLite базы.
        for statement in (
            "ALTER TABLE cart_items ADD COLUMN weight_min_kg REAL",
            "ALTER TABLE cart_items ADD COLUMN weight_max_kg REAL",
            "ALTER TABLE cart_items ADD COLUMN weight_estimated INTEGER DEFAULT 0",
            "ALTER TABLE order_items ADD COLUMN weight_min_kg REAL",
            "ALTER TABLE order_items ADD COLUMN weight_max_kg REAL",
            "ALTER TABLE order_items ADD COLUMN weight_estimated INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN referred_by INTEGER",
            "ALTER TABLE users ADD COLUMN balance_rub REAL DEFAULT 0",
            "ALTER TABLE orders ADD COLUMN weight_kg REAL",
            "ALTER TABLE orders ADD COLUMN weight_set INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN client_code TEXT",
        ):
            try:
                await db.execute(statement)
            except Exception as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise
        await db.commit()


async def ensure_user(user_id: int, username: str, full_name: str, referred_by: int = None):
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if row is None:
            if referred_by == user_id:
                referred_by = None
            await db.execute(
                "INSERT INTO users (user_id, username, full_name, phone, referred_by, balance_rub, created_at) "
                "VALUES (?, ?, ?, ?, ?, 0, ?)",
                (user_id, username, full_name, None, referred_by, datetime.utcnow().isoformat()),
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


async def _generate_unique_client_code(db) -> str:
    while True:
        code = f"RK-{random.randint(100000, 999999)}"
        cur = await db.execute("SELECT 1 FROM users WHERE client_code = ?", (code,))
        if await cur.fetchone() is None:
            return code


async def ensure_client_code(user_id: int) -> str:
    """Возвращает код клиента, создавая его при первом обращении (первом заказе)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT client_code FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        if row and row["client_code"]:
            return row["client_code"]

        code = await _generate_unique_client_code(db)
        await db.execute(
            "UPDATE users SET client_code = ? WHERE user_id = ?", (code, user_id)
        )
        await db.commit()
        return code


async def add_cart_item(user_id: int, link: str, photo_id: str, price_yuan: float,
                         quantity: int, size: str, cost_rub: float,
                         weight_kg: float = None, shipping_rub: float = 0,
                         weight_min_kg: float = None, weight_max_kg: float = None,
                         weight_estimated: bool = False):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO cart_items
               (user_id, link, photo_id, price_yuan, quantity, size, weight_kg, weight_min_kg, weight_max_kg, weight_estimated, shipping_rub, cost_rub, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (user_id, link, photo_id, price_yuan, quantity, size, weight_kg, weight_min_kg, weight_max_kg, int(weight_estimated), shipping_rub, cost_rub,
             datetime.utcnow().isoformat()),
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
                """INSERT INTO order_items
                   (order_id, link, photo_id, price_yuan, quantity, size, weight_kg, weight_min_kg, weight_max_kg, weight_estimated, shipping_rub, cost_rub)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (order_id, i["link"], i["photo_id"], i["price_yuan"], i["quantity"], i["size"],
                 i["weight_kg"], i["weight_min_kg"], i["weight_max_kg"], i["weight_estimated"],
                 i["shipping_rub"], i["cost_rub"]),
            )
        await db.commit()
    await clear_cart(user_id)
    await ensure_client_code(user_id)
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


async def get_referral_stats(user_id: int) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT COUNT(*) AS cnt FROM users WHERE referred_by = ?", (user_id,)
        )
        count_row = await cur.fetchone()
        cur = await db.execute(
            "SELECT balance_rub FROM users WHERE user_id = ?", (user_id,)
        )
        balance_row = await cur.fetchone()
        return {
            "referrals_count": count_row["cnt"] if count_row else 0,
            "balance_rub": balance_row["balance_rub"] if balance_row else 0,
        }


async def add_balance(user_id: int, amount: float):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE users SET balance_rub = balance_rub + ? WHERE user_id = ?",
            (amount, user_id),
        )
        await db.commit()


async def spend_balance(user_id: int, amount: float):
    """Списывает сумму с баланса, не уходя ниже нуля. Возвращает фактически списанную сумму."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT balance_rub FROM users WHERE user_id = ?", (user_id,))
        row = await cur.fetchone()
        available = row["balance_rub"] if row else 0
        spend = min(available, amount)
        if spend > 0:
            await db.execute(
                "UPDATE users SET balance_rub = balance_rub - ? WHERE user_id = ?",
                (spend, user_id),
            )
            await db.commit()
        return round(spend, 2)


async def set_order_weight(order_id: int, weight_kg: float, price_per_kg: float, referral_bonus_per_kg: float):
    """Менеджер вводит фактический вес заказа после взвешивания на складе.
    Пересчитывает доставку и итог заказа, и если заказчик пришёл по рефералке —
    начисляет пригласившему бонус на баланс. Возвращает dict с деталями для уведомлений."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order = await cur.fetchone()
        if order is None:
            return None
        if order["weight_set"]:
            return {"already_set": True}

        shipping = round(weight_kg * price_per_kg, 2)
        new_total = round(order["total_rub"] + shipping, 2)

        await db.execute(
            "UPDATE orders SET weight_kg = ?, weight_set = 1, total_rub = ? WHERE id = ?",
            (weight_kg, new_total, order_id),
        )
        await db.commit()

        cur = await db.execute("SELECT referred_by FROM users WHERE user_id = ?", (order["user_id"],))
        user_row = await cur.fetchone()
        referred_by = user_row["referred_by"] if user_row else None

        bonus_credited = 0
        if referred_by:
            bonus_credited = round(weight_kg * referral_bonus_per_kg, 2)
            await db.execute(
                "UPDATE users SET balance_rub = balance_rub + ? WHERE user_id = ?",
                (bonus_credited, referred_by),
            )
            await db.commit()

        return {
            "already_set": False,
            "shipping_rub": shipping,
            "new_total": new_total,
            "referred_by": referred_by,
            "bonus_credited": bonus_credited,
        }
