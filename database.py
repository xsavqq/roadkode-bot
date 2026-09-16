from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.fsm.context import FSMContext

import database as db

from config import (
    REFERRAL_BONUS_PER_KG,
)

from states import CabinetStates

from keyboards import main_menu


router = Router()


# =========================================================
# СТАТУСЫ
# =========================================================

STATUS_EMOJI = {

    "Новая": "🆕",

    "В обработке": "⏳",

    "Выкуплен": "💰",

    "На складе в Китае": "🏭",

    "Отправлен": "🚚",

    "Доставлен": "✅",

    "Отменён": "❌",
}


# =========================================================
# ЛИЧНЫЙ КАБИНЕТ
# =========================================================

@router.message(
    F.text == "👤 Личный кабинет"
)
async def cabinet(
    message: Message,
    state: FSMContext,
):

    user = await db.get_user(
        message.from_user.id
    )

    if (
        user
        and user["phone"]
    ):

        stats = await db.get_referral_stats(
            message.from_user.id
        )

        await message.answer(

            "👤 <b>Личный кабинет</b>\n\n"

            f"Имя: "
            f"{user['full_name']}\n"

            f"Телефон: "
            f"{user['phone']}\n"

            f"Telegram: "
            f"@{user['username'] or '—'}\n\n"

            f"👥 Приглашено рефералов: "
            f"<b>{stats['referrals_count']}</b>\n"

            f"💰 Бонусный баланс: "
            f"<b>{stats['balance_rub']:.0f} ₽</b>\n\n"

            "Баланс можно использовать "
            "как скидку на следующий заказ.",

            reply_markup=main_menu,
        )

    else:

        await state.set_state(
            CabinetStates.waiting_phone
        )

        await message.answer(

            "📱 <b>Укажите номер телефона "
            "для связи.</b>\n\n"

            "Например:\n"
            "<b>+79991234567</b>"
        )


# =========================================================
# ПРИГЛАСИТЬ ДРУГА
# =========================================================

@router.message(
    F.text == "👥 Пригласить друга"
)
async def invite_friend(
    message: Message,
    bot: Bot,
):

    me = await bot.get_me()

    ref_link = (
        f"https://t.me/"
        f"{me.username}"
        f"?start=ref_"
        f"{message.from_user.id}"
    )

    stats = await db.get_referral_stats(
        message.from_user.id
    )

    await message.answer(

        "👥 <b>Реферальная программа</b>\n\n"

        "Приглашайте друзей в ROADKODE.\n\n"

        f"🎁 За каждый фактический кг "
        "заказа вашего реферала после "
        "взвешивания вам начисляется "
        f"<b>{REFERRAL_BONUS_PER_KG:.0f} ₽</b>.\n\n"

        "💰 Бонус поступает на ваш баланс "
        "и может использоваться "
        "как скидка на следующие заказы.\n\n"

        "🔗 <b>Ваша персональная ссылка:</b>\n"
        f"{ref_link}\n\n"

        f"👥 Приглашено: "
        f"<b>{stats['referrals_count']}</b>\n"

        f"💰 Баланс: "
        f"<b>{stats['balance_rub']:.0f} ₽</b>",

        reply_markup=main_menu,
    )


# =========================================================
# ТЕЛЕФОН
# =========================================================

@router.message(
    CabinetStates.waiting_phone,
    F.text,
)
async def got_phone(
    message: Message,
    state: FSMContext,
):

    phone = message.text.strip()

    if len(phone) < 5:

        await message.answer(
            "⚠️ Введите корректный номер телефона."
        )

        return

    await db.set_phone(
        message.from_user.id,
        phone,
    )

    await state.clear()

    await message.answer(

        "✅ <b>Телефон сохранён.</b>\n\n"
        "Теперь личный кабинет доступен.",

        reply_markup=main_menu,
    )


# =========================================================
# ТЕКСТ ЗАЯВОК
# =========================================================

async def _orders_text(
    user_id: int,
) -> str:

    orders = await db.get_user_orders(
        user_id
    )

    if not orders:

        return (
            "📨 <b>У вас пока нет заявок.</b>"
        )

    lines = [
        "📨 <b>Ваши заявки:</b>\n"
    ]

    for order in orders:

        emoji = STATUS_EMOJI.get(
            order["status"],
            "•",
        )

        line = (

            f"{emoji} "
            f"<b>Заявка №{order['id']}</b>\n"

            f"Статус: "
            f"<b>{order['status']}</b>\n"

            f"Сумма: "
            f"<b>{order['total_rub']:.0f} ₽</b>"
        )

        if (
            order["weight_set"]
            and order["weight_kg"]
            is not None
        ):

            line += (

                f"\n⚖️ Вес: "
                f"<b>{order['weight_kg']:.2f} кг</b>"
            )

        lines.append(line)

    return "\n\n".join(
        lines
    )


# =========================================================
# МОИ ЗАЯВКИ
# =========================================================

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


# =========================================================
# ОБНОВИТЬ СТАТУСЫ
# =========================================================

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
