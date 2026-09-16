from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from config import CLOSED_CHAT_URL, CLOSED_CHANNEL_URL


main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛒 Новый заказ")],
        [
            KeyboardButton(text="ℹ️ О боте"),
            KeyboardButton(text="📦 Как оформить заказ"),
        ],
        [
            KeyboardButton(text="📨 Мои заявки"),
            KeyboardButton(text="👤 Личный кабинет"),
        ],
        [KeyboardButton(text="🔄 Обновить статусы")],
        [KeyboardButton(text="🔒 Закрытый чат и канал")],
    ],
    resize_keyboard=True,
)


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


def cart_item_kb(item_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Изменить",
                    callback_data=f"edit_item:{item_id}",
                ),
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=f"del_item:{item_id}",
                ),
            ]
        ]
    )


closed_links_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(
                text="💬 Закрытый чат",
                url=CLOSED_CHAT_URL,
            )
        ],
        [
            InlineKeyboardButton(
                text="📢 Закрытый канал",
                url=CLOSED_CHANNEL_URL,
            )
        ],
    ]
)


STATUS_OPTIONS = [
    "В обработке",
    "Выкуплен",
    "На складе в Китае",
    "Отправлен",
    "Доставлен",
    "Отменён",
]


def admin_status_kb(order_id: int) -> InlineKeyboardMarkup:
    rows = []
    row = []

    for i, status in enumerate(STATUS_OPTIONS, 1):
        row.append(
            InlineKeyboardButton(
                text=status,
                callback_data=f"set_status:{order_id}:{status}",
            )
        )

        if i % 2 == 0:
            rows.append(row)
            row = []

    if row:
        rows.append(row)

    return InlineKeyboardMarkup(inline_keyboard=rows)


skip_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="-")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)
