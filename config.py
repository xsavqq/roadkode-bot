import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота, полученный у @BotFather в Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Telegram ID менеджера (или ID группы менеджеров), куда будут прилетать заявки.
# Узнать свой ID можно у бота @userinfobot
MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID", "0"))

# ==== Формула расчёта стоимости товара ====
# Итог (₽) = цена_в_юанях * EXCHANGE_RATE * (1 + MARKUP_PERCENT/100) * количество
EXCHANGE_RATE = float(os.getenv("EXCHANGE_RATE", "13.2"))   # курс юаня к рублю
MARKUP_PERCENT = float(os.getenv("MARKUP_PERCENT", "7"))     # ваш процент/наценка

# ==== Расчёт доставки по весу ====
# Стоимость доставки (₽) = вес_кг * PRICE_PER_KG
PRICE_PER_KG = float(os.getenv("PRICE_PER_KG", "800"))       # цена доставки за 1 кг, ₽

# Ссылки для кнопки "Закрытый чат и канал" — поменяйте на свои
CLOSED_CHAT_URL = os.getenv("CLOSED_CHAT_URL", "https://t.me/+your_chat_invite")
CLOSED_CHANNEL_URL = os.getenv("CLOSED_CHANNEL_URL", "https://t.me/+your_channel_invite")

# Название бота, показывается в текстах
BOT_NAME = os.getenv("BOT_NAME", "Cargo Hub")

DB_PATH = os.getenv("DB_PATH", "bot.db")


def calc_cost(price_yuan: float, quantity: int) -> float:
    """Считает стоимость товара в рублях по заданной формуле."""
    total = price_yuan * EXCHANGE_RATE * (1 + MARKUP_PERCENT / 100) * quantity
    return round(total, 2)


def calc_shipping(weight_kg: float) -> float:
    """Считает стоимость доставки в рублях по весу товара."""
    return round(weight_kg * PRICE_PER_KG, 2)


def yuan_rate_text() -> str:
    """Текст с текущим курсом юаня — показывается в начале оформления заказа."""
    return (
        f"🧮 Текущий курс юаня: {EXCHANGE_RATE:.2f} ₽ / ¥\n"
        f"Бот рассчитывает стоимость товара по этому курсу и добавляет комиссию сервиса.\n\n"
        f"📦 Доставка: {PRICE_PER_KG:.0f} ₽ / кг"
    )
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.6-luna")
