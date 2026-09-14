from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

import database as db

router = Router()


@router.callback_query(F.data.startswith("set_status:"))
async def set_status(callback: CallbackQuery, bot: Bot):
    _, order_id_str, status = callback.data.split(":", 2)
    order_id = int(order_id_str)

    await db.set_order_status(order_id, status)
    order = await db.get_order(order_id)

    # Обновляем сообщение у менеджера
    await callback.message.edit_text(
        callback.message.text.split("\nСтатус:")[0] + f"\nСтатус: {status}",
        reply_markup=callback.message.reply_markup,
    )
    await callback.answer(f"Статус изменён: {status}")

    # Уведомляем клиента
    try:
        await bot.send_message(
            order["user_id"],
            f"🔔 Статус заявки №{order_id} изменён: {status}",
        )
    except Exception:
        pass  # пользователь мог заблокировать бота
