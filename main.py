import asyncio
import logging

from aiogram import (
    Bot,
    Dispatcher,
)

from aiogram.client.default import (
    DefaultBotProperties,
)

from aiogram.enums import (
    ParseMode,
)

from aiogram.fsm.storage.memory import (
    MemoryStorage,
)


from config import BOT_TOKEN

import database as db


from handlers import (
    start,
    order,
    cart,
    cabinet,
    admin,
)


# =========================================================
# MAIN
# =========================================================

async def main():

    logging.basicConfig(
        level=logging.INFO
    )

    # -----------------------------------------------------
    # ПРОВЕРКА ТОКЕНА
    # -----------------------------------------------------

    if not BOT_TOKEN:

        raise RuntimeError(

            "Не задан BOT_TOKEN. "
            "Добавьте BOT_TOKEN "
            "в Railway Variables."
        )

    # -----------------------------------------------------
    # DATABASE
    # -----------------------------------------------------

    await db.init_db()

    # -----------------------------------------------------
    # BOT
    # -----------------------------------------------------

    bot = Bot(

        token=BOT_TOKEN,

        default=DefaultBotProperties(

            parse_mode=ParseMode.HTML
        ),
    )

    # -----------------------------------------------------
    # DISPATCHER
    # -----------------------------------------------------

    dp = Dispatcher(

        storage=MemoryStorage()
    )

    # -----------------------------------------------------
    # ROUTERS
    # -----------------------------------------------------

    dp.include_router(
        start.router
    )

    dp.include_router(
        order.router
    )

    dp.include_router(
        cart.router
    )

    dp.include_router(
        cabinet.router
    )

    dp.include_router(
        admin.router
    )

    # -----------------------------------------------------
    # WEBHOOK
    # -----------------------------------------------------

    await bot.delete_webhook(
        drop_pending_updates=True
    )

    # -----------------------------------------------------
    # START
    # -----------------------------------------------------

    await dp.start_polling(
        bot
    )


# =========================================================
# ENTRY POINT
# =========================================================

if __name__ == "__main__":

    asyncio.run(
        main()
    )
