import os
from dotenv import load_dotenv

load_dotenv()

# Токен бота, полученный у @BotFather в Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Telegram ID менеджера (или ID группы менеджеров), куда будут прилетать заявки.
# Узнать свой ID можно у бота @userinfobot
MANAGER_CHAT_ID = int(os.getenv("MANAGER_CHAT_ID", "0"))

# ==== Формула расчёта стоимости ====
# Итог (₽) = цена_в_юанях * EXCHANGE_RATE * (1 + MARKUP_PERCENT/100) * количество
EXCHANGE_RATE = float(os.getenv("EXCHANGE_RATE", "13.2"))   # курс юаня к рублю
MARKUP_PERCENT = float(os.getenv("MARKUP_PERCENT", "7"))     # ваш процент/наценка

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
