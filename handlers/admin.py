from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

import database as db
from config import (
    MANAGER_CHAT_ID,
    PRICE_PER_KG,
    REFERRAL_BONUS_PER_KG,
)
from states import AdminStates

router = Router()


def _is_manager(message: Message) -> bool:
    """
    Проверяем, что действие выполняется в чате менеджера.

    MANAGER_CHAT_ID должен совпадать с Telegram ID личного чата
    менеджера либо с ID группы менеджеров.
    """
    return bool(MANAGER_CHAT_ID and message.chat.id == MANAGER_CHAT_ID)


def _is_manager_callback(callback: CallbackQuery) -> bool:
    """
    Проверка callback от менеджера.

    Callback-кнопки для изменения статуса и веса должны работать
    только внутри чата менеджера.
    """
    if not MANAGER_CHAT_ID or not callback.message:
        return False

    return callback.message.chat.id == MANAGER_CHAT_ID


def _manager_item_text(item) -> str:
    lines = [
        f"Товар: {item['link'] or '📎 фото / без ссылки'}",
        f"Цена: {item['price_yuan']:.0f} ¥ × {item['quantity']} шт.",
        f"Размер: {item['size'] or 'не указан'}",
    ]

    if item["weight_estimated"]:
        min_weight = item["weight_min_kg"]
        max_weight = item["weight_max_kg"]

        if min_weight is not None and max_weight is not None:
            lines.append(
                f"🤖 Примерный вес 1 шт.: "
                f"{min_weight:.2f}–{max_weight:.2f} кг"
            )

        lines.append("⚠️ Вес ориентировочный")
        lines.append(
            "🚚 Доставка: НЕ включена — "
            "уточнить после фактического взвешивания"
        )
        lines.append(
            f"💰 К оплате сейчас: {item['cost_rub']:.0f} ₽"
        )

    elif item["weight_kg"]:
        lines.append(
            f"⚖️ Вес: {item['weight_kg']:.2f} кг"
        )

        if item["shipping_rub"]:
            lines.append(
                f"🚚 Доставка: {item['shipping_rub']:.0f} ₽"
            )

        lines.append(
            f"💰 Стоимость: {item['cost_rub']:.0f} ₽"
        )

    else:
        lines.append("⚖️ Вес: не указан")
        lines.append(
            f"💰 Стоимость: {item['cost_rub']:.0f} ₽"
        )

    return "\n".join(lines)


# =========================================================
# ИЗМЕНЕНИЕ СТАТУСА ЗАКАЗА
# =========================================================

@router.callback_query(F.data.startswith("set_status:"))
async def set_status(
    callback: CallbackQuery,
    bot: Bot,
):
    if not _is_manager_callback(callback):
        await callback.answer(
            "⛔ У вас нет доступа.",
            show_alert=True,
        )
        return

    try:
        _, order_id_str, status = callback.data.split(":", 2)
        order_id = int(order_id_str)
    except (ValueError, AttributeError):
        await callback.answer(
            "⚠️ Некорректные данные.",
            show_alert=True,
        )
        return

    order = await db.get_order(order_id)

    if order is None:
        await callback.answer(
            "⚠️ Заявка не найдена.",
            show_alert=True,
        )
        return

    await db.set_order_status(order_id, status)

    order = await db.get_order(order_id)
    order_items = await db.get_order_items(order_id)

    original_text = callback.message.text or ""

    if "\n\n" in original_text:
        header = original_text.split("\n\n", 1)[0]
    else:
        header = original_text

    body = "\n\n".join(
        _manager_item_text(item)
        for item in order_items
    )

    weight_line = ""

    if order["weight_set"] and order["weight_kg"] is not None:
        weight_line = (
            f"\n⚖️ Фактический вес заказа: "
            f"{order['weight_kg']:.2f} кг"
        )

    manager_text = (
        f"{header}\n\n"
        f"{body}\n\n"
        f"Итого к оплате сейчас: "
        f"{order['total_rub']:.0f} ₽"
        f"{weight_line}\n"
        f"Статус: {status}"
    )

    try:
        await callback.message.edit_text(
            manager_text,
            reply_markup=callback.message.reply_markup,
        )
    except Exception:
        pass

    await callback.answer(
        f"Статус изменён: {status}"
    )

    # Уведомляем клиента
    try:
        await bot.send_message(
            order["user_id"],
            f"🔔 <b>Обновление заявки №{order_id}</b>\n\n"
            f"Статус: <b>{status}</b>",
        )
    except Exception as exc:
        print(
            "CLIENT STATUS NOTIFICATION ERROR:",
            repr(exc),
            flush=True,
        )


# =========================================================
# ВВОД ФАКТИЧЕСКОГО ВЕСА
# =========================================================

@router.callback_query(F.data.startswith("set_weight:"))
async def ask_order_weight(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not _is_manager_callback(callback):
        await callback.answer(
            "⛔ У вас нет доступа.",
            show_alert=True,
        )
        return

    try:
        order_id = int(
            callback.data.split(":", 1)[1]
        )
    except (ValueError, AttributeError):
        await callback.answer(
            "⚠️ Некорректный номер заявки.",
            show_alert=True,
        )
        return

    order = await db.get_order(order_id)

    if order is None:
        await callback.answer(
            "⚠️ Заявка не найдена.",
            show_alert=True,
        )
        return

    if order["weight_set"]:
        await callback.answer(
            "⚠️ Вес этой заявки уже указан.",
            show_alert=True,
        )
        return

    await state.set_state(
        AdminStates.waiting_order_weight
    )

    await state.update_data(
        order_id=order_id
    )

    await callback.message.answer(
        f"⚖️ <b>Фактический вес заявки №{order_id}</b>\n\n"
        f"Введите вес заказа в кг.\n"
        f"Например: <b>1.4</b>\n\n"
        f"🚚 Доставка считается:\n"
        f"<b>вес × {PRICE_PER_KG:.0f} ₽/кг</b>"
    )

    await callback.answer()


# =========================================================
# ОБРАБОТКА ФАКТИЧЕСКОГО ВЕСА
# =========================================================

@router.message(
    AdminStates.waiting_order_weight,
    F.text,
)
async def got_order_weight(
    message: Message,
    state: FSMContext,
    bot: Bot,
):
    if not _is_manager(message):
        await state.clear()

        await message.answer(
            "⛔ У вас нет доступа."
        )
        return

    raw = (
        message.text
        .strip()
        .replace(",", ".")
    )

    try:
        weight = float(raw)

        if weight <= 0:
            raise ValueError

        if weight > 500:
            raise ValueError

    except ValueError:
        await message.answer(
            "⚠️ Введите корректный вес.\n\n"
            "Например: <b>1.4</b>"
        )
        return

    data = await state.get_data()
    order_id = data.get("order_id")

    if not order_id:
        await state.clear()

        await message.answer(
            "⚠️ Не удалось определить заявку."
        )
        return

    result = await db.set_order_weight(
        order_id,
        weight,
        PRICE_PER_KG,
        REFERRAL_BONUS_PER_KG,
    )

    await state.clear()

    if result is None:
        await message.answer(
            "⚠️ Заявка не найдена."
        )
        return

    if result.get("already_set"):
        await message.answer(
            "⚠️ Вес для этой заявки уже был указан ранее."
        )
        return

    order = await db.get_order(order_id)

    if order is None:
        await message.answer(
            "⚠️ Заявка не найдена после обновления."
        )
        return

    shipping = result["shipping_rub"]
    new_total = result["new_total"]

    # Сообщение менеджеру
    await message.answer(
        f"✅ <b>Вес заявки №{order_id} сохранён</b>\n\n"
        f"⚖️ Фактический вес: <b>{weight:.2f} кг</b>\n"
        f"🚚 Доставка: <b>{shipping:.0f} ₽</b>\n"
        f"💰 Новый итог: <b>{new_total:.0f} ₽</b>"
    )

    # =====================================================
    # УВЕДОМЛЕНИЕ КЛИЕНТУ
    # =====================================================

    try:
        await bot.send_message(
            order["user_id"],
            f"⚖️ <b>Заявка №{order_id} взвешена</b>\n\n"
            f"Фактический вес: <b>{weight:.2f} кг</b>\n"
            f"🚚 Доставка: <b>{shipping:.0f} ₽</b>\n\n"
            f"💰 Итоговая сумма заказа: "
            f"<b>{new_total:.0f} ₽</b>",
        )

    except Exception as exc:
        print(
            "CLIENT WEIGHT NOTIFICATION ERROR:",
            repr(exc),
            flush=True,
        )

    # =====================================================
    # РЕФЕРАЛЬНЫЙ БОНУС
    # =====================================================

    referred_by = result.get("referred_by")
    bonus_credited = result.get(
        "bonus_credited",
        0,
    )

    if referred_by and bonus_credited > 0:
        try:
            await bot.send_message(
                referred_by,
                f"🎁 <b>Вам начислен реферальный бонус!</b>\n\n"
                f"Ваш реферал оформил заказ.\n"
                f"Вес заказа: <b>{weight:.2f} кг</b>\n\n"
                f"💰 Начислено: "
                f"<b>{bonus_credited:.0f} ₽</b>\n\n"
                "Бонус можно использовать как скидку "
                "на следующий заказ.\n\n"
                "Проверить баланс можно в "
                "«👤 Личный кабинет».",
            )

        except Exception as exc:
            print(
                "REFERRAL BONUS NOTIFICATION ERROR:",
                repr(exc),
                flush=True,
            )
