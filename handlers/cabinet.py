from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

import database as db
from keyboards import main_menu


router = Router()


STATUS_EMOJI = {
    "Новая": "🆕",
    "В обработке": "⏳",
    "Выкуплен": "💰",
    "На складе в Китае": "🏭",
    "Отправлен": "🚚",
    "Доставлен": "✅",
    "Отменён": "❌",
}


async def _orders_text(
    user_id: int,
) -> str:

    orders = await db.get_user_orders(
        user_id
    )

    if not orders:
        return (
            "📨 <b>Ваши заявки:</b>\n\n"
            "У вас пока нет заявок."
        )

    lines = [
        "📨 <b>Ваши заявки:</b>\n"
    ]

    for order in orders:
        emoji = STATUS_EMOJI.get(
            order["status"],
            "•",
        )

        lines.append(
            f"{emoji} Заявка №{order['id']} — "
            f"{order['total_rub']:.0f} ₽ — "
            f"{order['status']}"
        )

    return "\n".join(lines)


@router.message(
    F.text == "👤 Личный кабинет"
)
async def cabinet(
    message: Message,
    state: FSMContext,
):
    # На всякий случай сбрасываем
    # незавершённое оформление заказа.
    await state.clear()

    orders = await db.get_user_orders(
        message.from_user.id
    )

    # Если заказов ещё нет,
    # код клиента пока не создаём.
    if not orders:
        await message.answer(
            "👤 <b>Личный кабинет</b>\n\n"
            "🆔 Код клиента: пока не присвоен\n\n"
            "Оформите первый заказ — после его "
            "отправки менеджеру бот автоматически "
            "закрепит за вами персональный код клиента.",
            reply_markup=main_menu,
        )

        return

    # Если заказы уже есть,
    # получаем постоянный код клиента.
    client_code = await db.get_or_create_client_code(
        message.from_user.id
    )

    orders_text = await _orders_text(
        message.from_user.id
    )

    await message.answer(
        "👤 <b>Личный кабинет</b>\n\n"
        f"🆔 Ваш код клиента: "
        f"<b>{client_code}</b>\n\n"
        f"{orders_text}",
        reply_markup=main_menu,
    )


@router.message(
    F.text == "📨 Мои заявки"
)
async def my_orders(
    message: Message,
):
    await message.answer(
        await _orders_text(
            message.from_user.id
        ),
        reply_markup=main_menu,
    )


@router.message(
    F.text == "🔄 Обновить статусы"
)
async def refresh_statuses(
    message: Message,
):
    await message.answer(
        await _orders_text(
            message.from_user.id
        ),
        reply_markup=main_menu,
    )
