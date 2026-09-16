from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


# =========================================================
# ГЛАВНОЕ МЕНЮ
# =========================================================

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="🛒 Новый заказ"
            )
        ],
        [
            KeyboardButton(
                text="ℹ️ О боте"
            ),
            KeyboardButton(
                text="📦 Как оформить заказ"
            ),
        ],
        [
            KeyboardButton(
                text="📨 Мои заявки"
            ),
            KeyboardButton(
                text="👤 Личный кабинет"
            ),
        ],
        [
            KeyboardButton(
                text="👥 Пригласить друга"
            )
        ],
        [
            KeyboardButton(
                text="🔄 Обновить статусы"
            )
        ],
    ],
    resize_keyboard=True,
)


# =========================================================
# ОТМЕНА
# =========================================================

cancel_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="❌ Отмена"
            )
        ]
    ],
    resize_keyboard=True,
)


# =========================================================
# ПРОПУСТИТЬ / ОТМЕНИТЬ
# =========================================================

skip_cancel_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="-"
            ),
            KeyboardButton(
                text="❌ Отмена"
            ),
        ]
    ],
    resize_keyboard=True,
)


# =========================================================
# ПОСЛЕ ДОБАВЛЕНИЯ ТОВАРА
# =========================================================

def after_item_added_kb() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить товар",
                    callback_data="add_item",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🛒 Посмотреть корзину",
                    callback_data="view_cart",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📩 Отправить менеджеру",
                    callback_data="send_to_manager",
                )
            ],
        ]
    )


# =========================================================
# НИЖНЯЯ ЧАСТЬ КОРЗИНЫ
# =========================================================

def cart_footer_kb() -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ Добавить товар",
                    callback_data="add_item",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📩 Отправить менеджеру",
                    callback_data="send_to_manager",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Очистить корзину",
                    callback_data="clear_cart",
                )
            ],
        ]
    )


# =========================================================
# ДЕЙСТВИЯ С ТОВАРОМ В КОРЗИНЕ
# =========================================================

def cart_item_kb(
    item_id: int,
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Изменить цену",
                    callback_data=f"edit_item:{item_id}",
                ),
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=f"del_item:{item_id}",
                ),
            ]
        ]
    )


# =========================================================
# СТАТУСЫ ЗАКАЗА
# =========================================================

STATUS_OPTIONS = [
    "В обработке",
    "Выкуплен",
    "На складе в Китае",
    "Отправлен",
    "Доставлен",
    "Отменён",
]


# =========================================================
# КНОПКИ МЕНЕДЖЕРА
# =========================================================

def admin_status_kb(
    order_id: int,
    weight_set: bool = False,
) -> InlineKeyboardMarkup:

    rows = []

    row = []

    for i, status in enumerate(
        STATUS_OPTIONS,
        1,
    ):

        row.append(
            InlineKeyboardButton(
                text=status,
                callback_data=(
                    f"set_status:{order_id}:{status}"
                ),
            )
        )

        if i % 2 == 0:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    # Если фактический вес ещё не установлен —
    # показываем кнопку менеджеру.

    if not weight_set:

        rows.append(
            [
                InlineKeyboardButton(
                    text="⚖️ Указать вес заказа",
                    callback_data=(
                        f"set_weight:{order_id}"
                    ),
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


# =========================================================
# ТОЛЬКО ПРОПУСК
# =========================================================

skip_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(
                text="-"
            )
        ]
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)
