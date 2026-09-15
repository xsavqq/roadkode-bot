from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

import database as db


router = Router()


def _manager_item_text(
    item
) -> str:

    lines = [
        f"Товар: "
        f"{item['link'] or '📎 фото / без ссылки'}",

        f"Цена: "
        f"{item['price_yuan']:.0f} ¥ × "
        f"{item['quantity']} шт.",

        f"Размер: "
        f"{item['size'] or 'не указан'}",
    ]

    # =====================================================
    # AI-ВЕС
    # =====================================================

    if item["weight_estimated"]:

        min_weight = item[
            "weight_min_kg"
        ]

        max_weight = item[
            "weight_max_kg"
        ]

        if (
            min_weight is not None
            and max_weight is not None
        ):

            lines.append(
                f"🤖 Примерный вес 1 шт.: "
                f"{min_weight:.2f}–"
                f"{max_weight:.2f} кг"
            )

        lines.append(
            "⚠️ Вес ориентировочный"
        )

        lines.append(
            "🚚 Доставка: НЕ включена — "
            "уточнить после фактического "
            "взвешивания"
        )

        lines.append(
            f"💰 К оплате сейчас: "
            f"{item['cost_rub']:.0f} ₽"
        )

    # =====================================================
    # РУЧНОЙ ВЕС
    # =====================================================

    elif item["weight_kg"]:

        lines.append(
            f"⚖️ Вес: "
            f"{item['weight_kg']:.2f} кг"
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

    # =====================================================
    # ВЕС НЕ УКАЗАН
    # =====================================================

    else:

        lines.append(
            "⚖️ Вес: не указан"
        )

        lines.append(
            f"💰 Стоимость: "
            f"{item['cost_rub']:.0f} ₽"
        )

    return "\n".join(
        lines
    )


@router.callback_query(
    F.data.startswith("set_status:")
)
async def set_status(
    callback: CallbackQuery,
    bot: Bot
):

    _, order_id_str, status = (
        callback.data.split(
            ":",
            2
        )
    )

    order_id = int(
        order_id_str
    )

    await db.set_order_status(
        order_id,
        status
    )

    order = await db.get_order(
        order_id
    )

    order_items = (
        await db.get_order_items(
            order_id
        )
    )

    original_text = (
        callback.message.text
        or ""
    )

    header = (
        original_text
        .split(
            "\n\n",
            1
        )[0]
    )

    body = "\n\n".join(
        _manager_item_text(
            item
        )
        for item in order_items
    )

    manager_text = (
        f"{header}\n\n"
        f"{body}\n\n"
        f"Итого к оплате сейчас: "
        f"{order['total_rub']:.0f} ₽\n"
        f"Статус: {status}"
    )

    try:

        await callback.message.edit_text(
            manager_text,
            reply_markup=(
                callback.message.reply_markup
            )
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

            f"🔔 Статус заявки №"
            f"{order_id} изменён: "
            f"{status}"
        )

    except Exception:

        # Клиент мог заблокировать бота.
        pass
