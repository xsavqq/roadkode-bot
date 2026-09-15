```python
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
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL,
    link            TEXT,
    photo_id        TEXT,
    price_yuan      REAL NOT NULL,
    quantity        INTEGER NOT NULL,
    size            TEXT,
    weight_kg       REAL,
    weight_min_kg   REAL,
    weight_max_kg   REAL,
    weight_estimated INTEGER DEFAULT 0,
    shipping_rub    REAL DEFAULT 0,
    cost_rub        REAL NOT NULL,
    created_at      TEXT
);

CREATE TABLE IF NOT EXISTS orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    status      TEXT NOT NULL DEFAULT 'Новая',
    total_rub   REAL NOT NULL,
    created_at  TEXT
);

CREATE TABLE IF NOT EXISTS order_items (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id        INTEGER NOT NULL,
    link            TEXT,
    photo_id        TEXT,
    price_yuan      REAL NOT NULL,
    quantity        INTEGER NOT NULL,
    size            TEXT,
    weight_kg       REAL,
    weight_min_kg   REAL,
    weight_max_kg   REAL,
    weight_estimated INTEGER DEFAULT 0,
    shipping_rub    REAL DEFAULT 0,
    cost_rub        REAL NOT NULL
);
"""


async def _add_column_if_missing(db, table_name, column_name, column_type):
    """
    Добавляет колонку в существующую SQLite-базу,
    если её ещё нет.

    Это нужно для Railway: старая база не потеряется,
    новые поля AI добавятся автоматически.
    """

    cur = await db.execute(
        f"PRAGMA table_info({table_name})"
    )

    columns = await cur.fetchall()

    existing_columns = {
        column[1]
        for column in columns
    }

    if column_name not in existing_columns:
        await db.execute(
            f"ALTER TABLE {table_name} "
            f"ADD COLUMN {column_name} {column_type}"
        )


async def init_db():
    """
    Создаёт таблицы и автоматически обновляет
    существующую базу новыми полями.
    """

    async with aiosqlite.connect(DB_PATH) as db:

        await db.executescript(SCHEMA)

        # --------------------------------------------------
        # Миграция старой cart_items
        # --------------------------------------------------

        await _add_column_if_missing(
            db,
            "cart_items",
            "weight_min_kg",
            "REAL",
        )

        await _add_column_if_missing(
            db,
            "cart_items",
            "weight_max_kg",
            "REAL",
        )

        await _add_column_if_missing(
            db,
            "cart_items",
            "weight_estimated",
            "INTEGER DEFAULT 0",
        )

        # --------------------------------------------------
        # Миграция старой order_items
        # --------------------------------------------------

        await _add_column_if_missing(
            db,
            "order_items",
            "weight_min_kg",
            "REAL",
        )

        await _add_column_if_missing(
            db,
            "order_items",
            "weight_max_kg",
            "REAL",
        )

        await _add_column_if_missing(
            db,
            "order_items",
            "weight_estimated",
            "INTEGER DEFAULT 0",
        )

        await db.commit()


# ============================================================
# USERS
# ============================================================

async def ensure_user(
    user_id: int,
    username: str,
    full_name: str,
):
    async with aiosqlite.connect(DB_PATH) as db:

        cur = await db.execute(
            "SELECT user_id FROM users WHERE user_id = ?",
            (user_id,),
        )

        row = await cur.fetchone()

        if row is None:
            await db.execute(
                """
                INSERT INTO users
                (
                    user_id,
                    username,
                    full_name,
                    phone,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    full_name,
                    None,
                    datetime.utcnow().isoformat(),
                ),
            )

            await db.commit()


async def set_phone(
    user_id: int,
    phone: str,
):
    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            UPDATE users
            SET phone = ?
            WHERE user_id = ?
            """,
            (
                phone,
                user_id,
            ),
        )

        await db.commit()


async def get_user(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            """
            SELECT *
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        )

        return await cur.fetchone()


# ============================================================
# CART
# ============================================================

async def add_cart_item(
    user_id: int,
    link: str,
    photo_id: str,
    price_yuan: float,
    quantity: int,
    size: str,
    cost_rub: float,
    weight_kg: float = None,
    shipping_rub: float = 0,
    weight_min_kg: float = None,
    weight_max_kg: float = None,
    weight_estimated: int = 0,
):
    """
    Добавляет товар в корзину.

    Если weight_estimated = 1:
    - вес является примерным;
    - shipping_rub должен быть 0;
    - примерный диапазон хранится отдельно;
    - примерный вес НЕ увеличивает сумму заказа.
    """

    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            INSERT INTO cart_items
            (
                user_id,
                link,
                photo_id,
                price_yuan,
                quantity,
                size,
                weight_kg,
                weight_min_kg,
                weight_max_kg,
                weight_estimated,
                shipping_rub,
                cost_rub,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                link,
                photo_id,
                price_yuan,
                quantity,
                size,
                weight_kg,
                weight_min_kg,
                weight_max_kg,
                weight_estimated,
                shipping_rub,
                cost_rub,
                datetime.utcnow().isoformat(),
            ),
        )

        await db.commit()


async def get_cart(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            """
            SELECT *
            FROM cart_items
            WHERE user_id = ?
            ORDER BY id
            """,
            (user_id,),
        )

        return await cur.fetchall()


async def get_cart_total(user_id: int) -> float:
    """
    Считает текущую сумму заказа.

    Для AI-веса доставка равна 0,
    поэтому примерный вес никак не влияет
    на сумму к оплате.
    """

    items = await get_cart(user_id)

    return round(
        sum(
            i["cost_rub"]
            for i in items
        ),
        2,
    )


async def delete_cart_item(
    item_id: int,
    user_id: int,
):
    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            DELETE FROM cart_items
            WHERE id = ?
            AND user_id = ?
            """,
            (
                item_id,
                user_id,
            ),
        )

        await db.commit()


async def clear_cart(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            DELETE FROM cart_items
            WHERE user_id = ?
            """,
            (user_id,),
        )

        await db.commit()


async def get_cart_item(
    item_id: int,
    user_id: int,
):
    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            """
            SELECT *
            FROM cart_items
            WHERE id = ?
            AND user_id = ?
            """,
            (
                item_id,
                user_id,
            ),
        )

        return await cur.fetchone()


# ============================================================
# ORDERS
# ============================================================

async def create_order_from_cart(
    user_id: int,
) -> int | None:

    items = await get_cart(user_id)

    if not items:
        return None

    # В сумму заказа попадает только cost_rub.
    # AI-примерный вес и доставка по нему НЕ учитываются.
    total = round(
        sum(
            i["cost_rub"]
            for i in items
        ),
        2,
    )

    async with aiosqlite.connect(DB_PATH) as db:

        cur = await db.execute(
            """
            INSERT INTO orders
            (
                user_id,
                status,
                total_rub,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                "Новая",
                total,
                datetime.utcnow().isoformat(),
            ),
        )

        order_id = cur.lastrowid

        for i in items:

            await db.execute(
                """
                INSERT INTO order_items
                (
                    order_id,
                    link,
                    photo_id,
                    price_yuan,
                    quantity,
                    size,
                    weight_kg,
                    weight_min_kg,
                    weight_max_kg,
                    weight_estimated,
                    shipping_rub,
                    cost_rub
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    i["link"],
                    i["photo_id"],
                    i["price_yuan"],
                    i["quantity"],
                    i["size"],
                    i["weight_kg"],
                    i["weight_min_kg"],
                    i["weight_max_kg"],
                    i["weight_estimated"],
                    i["shipping_rub"],
                    i["cost_rub"],
                ),
            )

        await db.commit()

    await clear_cart(user_id)

    return order_id


async def get_order_items(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            """
            SELECT *
            FROM order_items
            WHERE order_id = ?
            """,
            (order_id,),
        )

        return await cur.fetchall()


async def get_user_orders(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            """
            SELECT *
            FROM orders
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (user_id,),
        )

        return await cur.fetchall()


async def get_order(order_id: int):
    async with aiosqlite.connect(DB_PATH) as db:

        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            """
            SELECT *
            FROM orders
            WHERE id = ?
            """,
            (order_id,),
        )

        return await cur.fetchone()


async def set_order_status(
    order_id: int,
    status: str,
):
    async with aiosqlite.connect(DB_PATH) as db:

        await db.execute(
            """
            UPDATE orders
            SET status = ?
            WHERE id = ?
            """,
            (
                status,
                order_id,
            ),
        )

        await db.commit()
```
