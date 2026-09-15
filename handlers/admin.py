from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

import database as db

router = Router()


def _manager_item_text(item) -> str:
    """
    Формирует информацию о товаре для менеджера.
    Отдельно показывает AI-оценку веса и факт,
    что доставка пока не включена в сумму.
    """

    lines = [
        f"Товар: {item['link'] or '📎 фото / без ссылки'}",
        f"Цена: {item['price_yuan']:.0f} ¥ × {item['quantity']} шт.",
        f"Размер: {item['size'] or 'не указан'}",
    ]

    # Вес определён AI
    if item["weight_estimated"]:
        min_weight = item["weight_min_kg"]
        max_weight = item["weight_max_kg"]

        if min_weight is not None and max_weight is not None:
            lines.append(
                f"🤖 Примерный вес 1 шт.: "
                f"{min_weight:.2f}–{max_weight:.2f} кг"
            )

        lines.append(
            "⚠️ Вес ориентировочный"
        )

        lines.append(
            "🚚 Доставка: НЕ включена — "
            "уточнить после фактического взвешивания"
        )

        lines.append(
            f"💰 К оплате сейчас: "
            f"{item['cost_rub']:.0f} ₽"
        )

    # Вес введён пользователем вручную
    elif item["weight_kg"]:
        lines.append(
            f"⚖️ Вес: {item['weight_kg']:.2f} кг"
        )

        if item["shipping_rub"]:
            lines.append(
                f"🚚 Доставка: "
                f"{item['shipping_rub']:.0f} ₽"
            )

        lines.append(
            f"💰 Стоимость: "
            f"{item['cost_rub']:.0f} ₽"
        )

    # Вес неизвестен
    else:
        lines.append(
            "⚖️ Вес: не указан"
        )

        lines.append(
            f"💰 Стоимость: "
            f"{item['cost_rub']:.0f} ₽"
        )

    return "\n".join(lines)


@router.callback_query(F.data.startswith("set_status:"))
async def set_status(
    callback: CallbackQuery,
    bot: Bot
):
    _, order_id_str, status = callback.data.split(":", 2)
    order_id = int(order_id_str)

    # Меняем статус в БД
    await db.set_order_status(
        order_id,
        status
    )

    order = await db.get_order(
        order_id
    )

    # Получаем актуальные товары заказа
    order_items = await db.get_order_items(
        order_id
    )

    # Данные клиента
    user_id = order["user_id"]

    # Формируем обновлённое сообщение менеджеру
    original_text = callback.message.text or ""

    # Убираем старую строку статуса,
    # чтобы при повторном изменении она не дублировалась.
    if "\nСтатус:" in original_text:
        header_and_body = original_text.split(
            "\nСтатус:",
            1
        )[0]
    else:
        header_and_body = original_text

    # Если по какой-то причине сообщение нельзя
    # корректно обновить — пересобираем его из БД.
    if not order_items:
        manager_text = (
            f"{header_and_body}\n"
            f"Статус: {status}"
        )
    else:
        # Сохраняем шапку заявки из текущего сообщения,
        # но заново формируем товары.
        if "\n\n" in header_and_body:
            header = header_and_body.split(
                "\n\n",
                1
            )[0]

            body = "\n\n".join(
                _manager_item_text(item)
                for item in order_items
            )

            manager_text = (
                f"{header}\n\n"
                f"{body}\n\n"
                f"Итого к оплате сейчас: "
                f"{order['total_rub']:.0f} ₽\n"
                f"Статус: {status}"
            )
        else:
            manager_text = (
                f"{header_and_body}\n"
                f"Статус: {status}"
            )

    # Обновляем сообщение менеджера
    try:
        await callback.message.edit_text(
            manager_text,
            reply_markup=callback.message.reply_markup,
        )
    except Exception:
        # Например, сообщение уже было изменено
        # или Telegram не разрешил повторное редактирование.
        pass

    await callback.answer(
        f"Статус изменён: {status}"
    )

    # Уведомляем клиента
    try:
        await bot.send_message(
            user_id,
            f"🔔 Статус заявки №{order_id} изменён: "
            f"{status}",
        )
    except Exception:
        # Клиент мог заблокировать бота
        pass
