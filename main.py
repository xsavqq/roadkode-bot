import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
import database as db

from handlers import start
from handlers import order
from handlers import cart
from handlers import cabinet
from handlers import admin


async def main():
    logging.basicConfig(
        level=logging.INFO
    )

    if not BOT_TOKEN:
        raise RuntimeError(
            "Не задан BOT_TOKEN. "
            "Добавьте BOT_TOKEN в Railway Variables."
        )

    # Инициализация базы данных
    await db.init_db()

    # Создаём бота
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        ),
    )

    # Создаём Dispatcher
    dp = Dispatcher(
        storage=MemoryStorage()
    )

    # =====================================================
    # ПОДКЛЮЧАЕМ ВСЕ ОБРАБОТЧИКИ
    # =====================================================

    dp.include_router(start.router)
    dp.include_router(order.router)
    dp.include_router(cart.router)
    dp.include_router(cabinet.router)
    dp.include_router(admin.router)

    # =====================================================
    # ЗАПУСК
    # =====================================================

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    logging.info(
        "ROADKODE BOT: routers successfully loaded"
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
