import os

from dotenv import load_dotenv


load_dotenv()


# =========================================================
# TELEGRAM
# =========================================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Telegram ID менеджера или группы менеджеров
MANAGER_CHAT_ID = int(
    os.getenv("MANAGER_CHAT_ID", "0")
)

# Username менеджера для связи с клиентом
MANAGER_USERNAME = os.getenv(
    "MANAGER_USERNAME",
    "@roadkode_mgr",
)


# =========================================================
# OPENAI
# =========================================================

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY",
    "",
)

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-4o-mini",
)


# =========================================================
# РАСЧЁТ СТОИМОСТИ ТОВАРА
# =========================================================

# Стоимость товара:
#
# цена в ¥
# × курс юаня
# × (1 + наценка)
# × количество
#
# Пример:
# 100 ¥ × 13.2 × 1.07 = 1412.4 ₽

EXCHANGE_RATE = float(
    os.getenv("EXCHANGE_RATE", "13.2")
)

MARKUP_PERCENT = float(
    os.getenv("MARKUP_PERCENT", "7")
)


# =========================================================
# ДОСТАВКА
# =========================================================

# Цена доставки за 1 кг
PRICE_PER_KG = float(
    os.getenv("PRICE_PER_KG", "800")
)


# =========================================================
# РЕФЕРАЛЬНАЯ ПРОГРАММА
# =========================================================

# Сколько рублей получает пригласивший
# за каждый фактический кг заказа реферала.

REFERRAL_BONUS_PER_KG = float(
    os.getenv(
        "REFERRAL_BONUS_PER_KG",
        "100",
    )
)


# =========================================================
# ССЫЛКИ
# =========================================================

CLOSED_CHAT_URL = os.getenv(
    "CLOSED_CHAT_URL",
    "https://t.me/+PNTIUGCHSow0ODRi",
)

CLOSED_CHANNEL_URL = os.getenv(
    "CLOSED_CHANNEL_URL",
    "https://t.me/ROADKODE",
)


# =========================================================
# НАЗВАНИЕ / БАЗА
# =========================================================

BOT_NAME = os.getenv(
    "BOT_NAME",
    "ROADKODE ORDER",
)

DB_PATH = os.getenv(
    "DB_PATH",
    "bot.db",
)


# =========================================================
# ФУНКЦИИ РАСЧЁТА
# =========================================================

def calc_cost(
    price_yuan: float,
    quantity: int,
) -> float:
    """
    Стоимость товара без доставки.

    Доставка НЕ входит сюда.
    Она добавляется только после фактического
    взвешивания заказа менеджером.
    """

    total = (
        price_yuan
        * EXCHANGE_RATE
        * (1 + MARKUP_PERCENT / 100)
        * quantity
    )

    return round(total, 2)


def calc_shipping(
    weight_kg: float,
) -> float:
    """
    Стоимость доставки по фактическому весу.
    """

    return round(
        weight_kg * PRICE_PER_KG,
        2,
    )


def yuan_rate_text() -> str:
    """
    Сообщение с текущим курсом юаня.
    """

    return (
        f"💱 <b>Текущий курс юаня:</b> "
        f"{EXCHANGE_RATE:.2f} ₽ / ¥\n\n"
        "Стоимость товара рассчитывается "
        "по этому курсу с учётом комиссии сервиса."
    )
