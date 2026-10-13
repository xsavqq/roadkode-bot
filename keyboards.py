from config import (
    ASSORTMENT_URL,
    REVIEWS_URL,
    manager_url,
)

from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


# Старая клавиатура снизу экрана. Не используется для показа,
# оставлена для совместимости (текстовые хендлеры по-прежнему
# реагируют на её кнопки у тех, у кого она ещё висит).
legacy_main_menu = ReplyKeyboardMarkup(
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
        [KeyboardButton(text="👥 Пригласить друга")],
        [KeyboardButton(text="🔄 Обновить статусы")],
    ],
    resize_keyboard=True,
)


def main_inline_kb() -> InlineKeyboardMarkup:
    """
    Главное меню: inline-кнопки в две колонки.
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Сделать заказ",
                    callback_data="menu:order",
                ),
                InlineKeyboardButton(
                    text="📦 Мои заказы",
                    callback_data="menu:track",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🧮 Калькулятор",
                    callback_data="menu:calc",
                ),
                InlineKeyboardButton(
                    text="🛍 Ассортимент",
                    url=ASSORTMENT_URL,
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⭐ Отзывы",
                    url=REVIEWS_URL,
                ),
                InlineKeyboardButton(
                    text="❓ FAQ",
                    callback_data="menu:faq",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👥 Пригласить друга",
                    callback_data="menu:ref",
                ),
                InlineKeyboardButton(
                    text="🎁 Бонусы",
                    callback_data="menu:bonus",
                ),
            ],
        ]
    )


# Везде, где раньше показывалась нижняя клавиатура,
# теперь показывается inline-меню под сообщением.
main_menu = main_inline_kb()


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏠 В меню",
                    callback_data="menu:home",
                )
            ]
        ]
    )


def calc_result_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 Сделать заказ",
                    callback_data="menu:order",
                ),
                InlineKeyboardButton(
                    text="💬 Написать менеджеру",
                    url=manager_url(),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔁 Посчитать ещё",
                    callback_data="menu:calc",
                ),
                InlineKeyboardButton(
                    text="🏠 В меню",
                    callback_data="menu:home",
                ),
            ],
        ]
    )


cancel_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❌ Отмена")]
    ],
    resize_keyboard=True,
)


skip_cancel_kb = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="-"),
            KeyboardButton(text="❌ Отмена"),
        ]
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


STATUS_OPTIONS = [
    "В обработке",
    "Выкуплен",
    "На складе в Китае",
    "Отправлен",
    "Доставлен",
    "Отменён",
]


def admin_status_kb(
    order_id: int,
    weight_set: bool = False,
) -> InlineKeyboardMarkup:

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

    if not weight_set:
        rows.append(
            [
                InlineKeyboardButton(
                    text="⚖️ Указать вес заказа",
                    callback_data=f"set_weight:{order_id}",
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


skip_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="-")]
    ],
    resize_keyboard=True,
    one_time_keyboard=True,
)
