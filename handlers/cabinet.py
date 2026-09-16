from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
from config import REFERRAL_BONUS_PER_KG
from states import CabinetStates
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
async def cabinet(message: Message, state: FSMContext):
    user = await db.get_user(message.from_user.id)
    if user and user["phone"]:
        stats = await db.get_referral_stats(message.from_user.id)
        await message.answer(
            f"👤 Личный кабинет\n\n"
            f"Имя: {user['full_name']}\n"
            f"Телефон: {user['phone']}\n"
            f"Telegram: @{user['username'] or '—'}\n\n"
            f"👥 Приглашено рефералов: {stats['referrals_count']}\n"
            f"💰 Бонусный баланс: {stats['balance_rub']:.0f} ₽\n"
            f"Баланс автоматически учитывается менеджером как скидка "
            f"на следующий заказ.",
            reply_markup=main_menu,
        )
    else:
        await state.set_state(CabinetStates.waiting_phone)
        await message.answer(
            "Для личного кабинета укажите номер телефона для связи (например: +79991234567):"
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


@router.message(CabinetStates.waiting_phone, F.text)
async def got_phone(message: Message, state: FSMContext):
    await db.set_phone(message.from_user.id, message.text.strip())
    await state.clear()
    await message.answer("✅ Телефон сохранён.", reply_markup=main_menu)


async def _orders_text(user_id: int) -> str:
    orders = await db.get_user_orders(user_id)
    if not orders:
        return "У вас пока нет заявок."
    lines = ["📨 Ваши заявки:\n"]
    for o in orders:
        emoji = STATUS_EMOJI.get(o["status"], "•")
        lines.append(f"{emoji} Заявка №{o['id']} — {o['total_rub']:.0f} ₽ — {o['status']}")
    return "\n".join(lines)


@router.message(F.text == "📨 Мои заявки")
async def my_orders(message: Message):
    await message.answer(await _orders_text(message.from_user.id), reply_markup=main_menu)


@router.message(F.text == "🔄 Обновить статусы")
async def refresh_statuses(message: Message):
    await message.answer(await _orders_text(message.from_user.id), reply_markup=main_menu)
