import aiosqlite
from datetime import datetime
from config import DB_PATH


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    full_name   TEXT,
    phone       TEXT,
    client_code TEXT UNIQUE,
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

        # Миграция существующей базы.
        # Если колонка уже есть — просто пропускаем ошибку.
        for statement in (
            "ALTER TABLE users ADD COLUMN client_code TEXT",
            "ALTER TABLE cart_items ADD COLUMN weight_min_kg REAL",
            "ALTER TABLE cart_items ADD COLUMN weight_max_kg REAL",
            "ALTER TABLE cart_items ADD COLUMN weight_estimated INTEGER DEFAULT 0",
            "ALTER TABLE order_items ADD COLUMN weight_min_kg REAL",
            "ALTER TABLE order_items ADD COLUMN weight_max_kg REAL",
            "ALTER TABLE order_items ADD COLUMN weight_estimated INTEGER DEFAULT 0",
        ):
            try:
                await db.execute(statement)
            except Exception as exc:
                if "duplicate column name" not in str(exc).lower():
                    raise

        await db.commit()


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
                    client_code,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    full_name,
                    None,
                    None,
                    datetime.utcnow().isoformat(),
                ),
            )
        else:
            await db.execute(
                """
                UPDATE users
                SET username = ?,
                    full_name = ?
                WHERE user_id = ?
                """,
                (
                    username,
                    full_name,
                    user_id,
                ),
            )

        await db.commit()


async def get_or_create_client_code(
    user_id: int,
) -> str:
    """
    Возвращает постоянный код клиента:

    RK-0001
    RK-0002
    RK-0003
    ...
    """

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row

        cur = await db.execute(
            """
            SELECT client_code
            FROM users
            WHERE user_id = ?
            """,
            (user_id,),
        )

        user = await cur.fetchone()

        # Если пользователя ещё нет — создаём.
        if user is None:
            await db.execute(
                """
                INSERT INTO users
                (
                    user_id,
                    username,
                    full_name,
                    phone,
                    client_code,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    "",
                    "",
                    None,
                    None,
                    datetime.utcnow().isoformat(),
                ),
            )

            await db.commit()

            client_code = None
        else:
            client_code = user["client_code"]

        # Если код уже существует — возвращаем его.
        if client_code:
            return client_code

        # Ищем максимальный существующий номер.
        cur = await db.execute(
            """
            SELECT client_code
            FROM users
            WHERE client_code IS NOT NULL
            """
        )

        rows = await cur.fetchall()

        max_number = 0

        for row in rows:
            code = row["client_code"] or ""

            if code.startswith("RK-"):
                try:
                    number = int(code[3:])
                    max_number = max(
                        max_number,
                        number,
                    )
                except ValueError:
                    pass

        new_number = max_number + 1

        client_code = f"RK-{new_number:04d}"

        await db.execute(
            """
            UPDATE users
            SET client_code = ?
            WHERE user_id = ?
            """,
            (
                client_code,
                user_id,
            ),
        )

        await db.commit()

        return client_code


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


async def set_phone(
    user_id: int,
    phone: str,
):
    # Оставлено для совместимости со старой базой.
    # Новый личный кабинет телефон НЕ запрашивает.

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
    weight_estimated: bool = False,
):
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
                int(weight_estimated),
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


async def get_cart_total(
    user_id: int,
) -> float:
    items = await get_cart(user_id)

    return round(
        sum(
            item["cost_rub"]
            for item in items
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


async def create_order_from_cart(
    user_id: int,
) -> int | None:

    items = await get_cart(user_id)

    if not items:
        return None

    # При первом оформлении заказа
    # автоматически закрепляем код клиента.
    await get_or_create_client_code(user_id)

    total = round(
        sum(
            item["cost_rub"]
            for item in items
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

        for item in items:
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
                    item["link"],
                    item["photo_id"],
                    item["price_yuan"],
                    item["quantity"],
                    item["size"],
                    item["weight_kg"],
                    item["weight_min_kg"],
                    item["weight_max_kg"],
                    item["weight_estimated"],
                    item["shipping_rub"],
                    item["cost_rub"],
                ),
            )

        await db.commit()

    await clear_cart(user_id)

    return order_id


async def get_order_items(
    order_id: int,
):
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


async def get_user_orders(
    user_id: int,
):
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


async def get_order(
    order_id: int,
):
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
