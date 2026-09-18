from aiogram import Router, F, Bot
from aiogram.types import Message

import database as db
from config import REFERRAL_BONUS_PER_KG
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


@router.message(F.text == "👤 Личный кабинет")
async def cabinet(message: Message):
    user = await db.get_user(message.from_user.id)

    if not user or not user["client_code"]:
        await message.answer(
            "👤 <b>Личный кабинет</b>\n\n"
            "Кабинет откроется после вашего первого заказа — "
            "у вас появится персональный код клиента, "
            "реферальный баланс и история заявок.\n\n"
            "Нажмите «🛒 Новый заказ», чтобы оформить первый заказ.",
            reply_markup=main_menu,
        )
        return

    stats = await db.get_referral_stats(message.from_user.id)
    orders = await db.get_user_orders(message.from_user.id)

    await message.answer(
        f"👤 <b>Личный кабинет</b>\n\n"
        f"🆔 Код клиента: <b>{user['client_code']}</b>\n"
        f"Имя: {user['full_name']}\n"
        f"Telegram: @{user['username'] or '—'}\n\n"
        f"📨 Заявок: {len(orders)}\n"
        f"👥 Приглашено рефералов: {stats['referrals_count']}\n"
        f"💰 Бонусный баланс: {stats['balance_rub']:.0f} ₽\n"
        f"Баланс учитывается менеджером как скидка на следующий заказ.",
        reply_markup=main_menu,
    )


@router.message(F.text == "👥 Пригласить друга")
async def invite_friend(message: Message, bot: Bot):
    me = await bot.get_me()
    ref_link = f"https://t.me/{me.username}?start=ref_{message.from_user.id}"
    stats = await db.get_referral_stats(message.from_user.id)

    await message.answer(
        "👥 <b>Реферальная программа</b>\n\n"
        "Приводите друзей — за каждый кг их заказа (после взвешивания на складе) "
        f"вам начисляется {REFERRAL_BONUS_PER_KG:.0f} ₽ на баланс. "
        "Баланс тратится как скидка на ваши следующие заказы.\n\n"
        f"🔗 Ваша персональная ссылка:\n{ref_link}\n\n"
        f"👥 Приглашено: {stats['referrals_count']}\n"
        f"💰 Баланс: {stats['balance_rub']:.0f} ₽",
        reply_markup=main_menu,
    )


async def _orders_text(user_id: int) -> str:
    orders = await db.get_user_orders(user_id)
    if not orders:
        return "У вас пока нет заявок."
    lines = ["📨 Ваши заявки:\n"]
    for o in orders:
        emoji = STATUS_EMOJI.get(o["status"], "•")
        line = f"{emoji} Заявка №{o['id']} — {o['total_rub']:.0f} ₽ — {o['status']}"
        if o["weight_set"] and o["weight_kg"] is not None:
            line += f" (вес {o['weight_kg']:.2f} кг)"
        lines.append(line)
    return "\n".join(lines)


@router.message(F.text == "📨 Мои заявки")
async def my_orders(message: Message):
    await message.answer(await _orders_text(message.from_user.id), reply_markup=main_menu)


@router.message(F.text == "🔄 Обновить статусы")
async def refresh_statuses(message: Message):
    await message.answer(await _orders_text(message.from_user.id), reply_markup=main_menu)
