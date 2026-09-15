import os
from dotenv import load_dotenv

load_dotenv()

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")

# Менеджер / группа менеджеров
MANAGER_CHAT_ID = int(
    os.getenv("MANAGER_CHAT_ID", "0")
)

# Стоимость товара
EXCHANGE_RATE = float(
    os.getenv("EXCHANGE_RATE", "13.2")
)

MARKUP_PERCENT = float(
    os.getenv("MARKUP_PERCENT", "7")
)

# Доставка для ТОВАРОВ, где вес введён вручную.
# AI-вес эту функцию не использует.
PRICE_PER_KG = float(
    os.getenv("PRICE_PER_KG", "800")
)

# Закрытый чат
CLOSED_CHAT_URL = os.getenv(
    "CLOSED_CHAT_URL",
    "https://t.me/+your_chat_invite"
)

CLOSED_CHANNEL_URL = os.getenv(
    "CLOSED_CHANNEL_URL",
    "https://t.me/+your_channel_invite"
)

BOT_NAME = os.getenv(
    "BOT_NAME",
    "ROADKODE ORDER"
)

DB_PATH = os.getenv(
    "DB_PATH",
    "bot.db"
)


def calc_cost(
    price_yuan: float,
    quantity: int
) -> float:
    """
    Стоимость товара без доставки.

    Цена ¥ × курс × комиссия × количество.
    """

    total = (
        price_yuan
        * EXCHANGE_RATE
        * (1 + MARKUP_PERCENT / 100)
        * quantity
    )

    return round(total, 2)


def calc_shipping(
    weight_kg: float
) -> float:
    """
    Используется только для ручного веса.
    AI-вес никогда сюда не передаётся.
    """

    return round(
        weight_kg * PRICE_PER_KG,
        2
    )


def yuan_rate_text() -> str:
    return (
        f"💱 Текущий курс юаня: "
        f"{EXCHANGE_RATE:.2f} ₽ / ¥\n\n"
        "Бот рассчитывает стоимость товара по этому "
        "курсу и добавляет комиссию сервиса."
    )
