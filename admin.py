from aiogram import Router, F, Bot
from aiogram.types import (
    CallbackQuery,
    Message,
)
from aiogram.fsm.context import FSMContext

import database as db

from config import (
    MANAGER_CHAT_ID,
    calc_cost,
)

from states import EditItemStates

from keyboards import (
    cart_footer_kb,
    cart_item_kb,
    admin_status_kb,
    main_menu,
)


router = Router()


# =========================================================
# ТЕКСТ ТОВАРА
# =========================================================

def _item_text(item) -> str:

    lines = [

        f"🔗 Товар: "
        f"{item['link'] or '📎 без ссылки'}",

        f"💴 Цена: "
        f"{item['price_yuan']:.2f} ¥",

        f"🔢 Количество: "
        f"{item['quantity']} шт.",

        f"📏 Размер: "
        f"{item['size'] or 'не указан'}",
    ]

    # -----------------------------------------------------
    # AI ВЕС
    # -----------------------------------------------------

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
                "🤖 Примерный вес 1 шт.: "
                f"{min_weight:.2f}–"
                f"{max_weight:.2f} кг"
            )

        lines.append(
            "⚠️ Вес ориентировочный"
        )

        lines.append(
            "🚚 Доставка: "
            "не включена — "
            "уточняется после "
            "фактического взвешивания"
        )

        lines.append(
            f"💰 К оплате сейчас: "
            f"{item['cost_rub']:.0f} ₽"
        )

    # -----------------------------------------------------
    # ФАКТИЧЕСКИЙ ВЕС
    # -----------------------------------------------------

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

    else:

        lines.append(
            "⚖️ Вес: будет определён "
            "после взвешивания"
        )

        lines.append(
            f"💰 Стоимость товара: "
            f"{item['cost_rub']:.0f} ₽"
        )

    return "\n".join(lines)


# =========================================================
# ПРОСМОТР КОРЗИНЫ
# =========================================================

@router.callback_query(
    F.data == "view_cart"
)
async def view_cart(
    callback: CallbackQuery,
):

    await show_cart(
        callback
    )


@router.message(
    F.text == "🛒 Посмотреть корзину"
)
async def view_cart_msg(
    message: Message,
):

    items = await db.get_cart(
        message.from_user.id
    )

    if not items:

        await message.answer(
            "🛒 <b>Корзина пуста.</b>",
            reply_markup=main_menu,
        )

        return

    for item in items:

        text = _item_text(item)

        if item["photo_id"]:

            await message.answer_photo(
                item["photo_id"],
                caption=text,
                reply_markup=cart_item_kb(
                    item["id"]
                ),
            )

        else:

            await message.answer(
                text,
                reply_markup=cart_item_kb(
                    item["id"]
                ),
            )

    total = await db.get_cart_total(
        message.from_user.id
    )

    await message.answer(

        f"🛒 <b>Общая сумма товаров:</b> "
        f"{total:.0f} ₽\n\n"

        "🚚 Доставка не включена.\n"
        "Она будет рассчитана после "
        "фактического взвешивания.",

        reply_markup=cart_footer_kb(),
    )


async def show_cart(
    callback: CallbackQuery,
):

    user_id = callback.from_user.id

    items = await db.get_cart(
        user_id
    )

    if not items:

        await callback.message.answer(
            "🛒 <b>Корзина пуста.</b>",
            reply_markup=main_menu,
        )

        await callback.answer()

        return

    for item in items:

        text = _item_text(item)

        if item["photo_id"]:

            await callback.message.answer_photo(
                item["photo_id"],
                caption=text,
                reply_markup=cart_item_kb(
                    item["id"]
                ),
            )

        else:

            await callback.message.answer(
                text,
                reply_markup=cart_item_kb(
                    item["id"]
                ),
            )

    total = await db.get_cart_total(
        user_id
    )

    await callback.message.answer(

        f"🛒 <b>Общая сумма товаров:</b> "
        f"{total:.0f} ₽\n\n"

        "🚚 Доставка не включена.\n"
        "Она будет рассчитана после "
        "фактического взвешивания.",

        reply_markup=cart_footer_kb(),
    )

    await callback.answer()


# =========================================================
# УДАЛЕНИЕ ТОВАРА
# =========================================================

@router.callback_query(
    F.data.startswith("del_item:")
)
async def delete_item(
    callback: CallbackQuery,
):

    try:

        item_id = int(
            callback.data.split(":")[1]
        )

    except (
        ValueError,
        IndexError,
    ):

        await callback.answer(
            "⚠️ Ошибка.",
            show_alert=True,
        )

        return

    await db.delete_cart_item(
        item_id,
        callback.from_user.id,
    )

    total = await db.get_cart_total(
        callback.from_user.id
    )

    try:

        await callback.message.edit_reply_markup(
            reply_markup=None
        )

    except Exception:
        pass

    await callback.message.answer(

        f"🗑 <b>Товар удалён.</b>\n\n"
        f"Общая сумма товаров: "
        f"<b>{total:.0f} ₽</b>",

        reply_markup=main_menu,
    )

    await callback.answer(
        "Удалено"
    )


# =========================================================
# НАЧАЛО РЕДАКТИРОВАНИЯ
# =========================================================

@router.callback_query(
    F.data.startswith("edit_item:")
)
async def edit_item_start(
    callback: CallbackQuery,
    state: FSMContext,
):

    try:

        item_id = int(
            callback.data.split(":")[1]
        )

    except (
        ValueError,
        IndexError,
    ):

        await callback.answer(
            "⚠️ Ошибка.",
            show_alert=True,
        )

        return

    item = await db.get_cart_item(
        item_id,
        callback.from_user.id,
    )

    if not item:

        await callback.answer(
            "Товар не найден.",
            show_alert=True,
        )

        return

    await state.set_state(
        EditItemStates.waiting_new_price
    )

    await state.update_data(
        item_id=item_id
    )

    await callback.message.answer(

        f"💴 Текущая цена: "
        f"<b>{item['price_yuan']:.2f} ¥</b>\n"

        f"🔢 Количество: "
        f"<b>{item['quantity']} шт.</b>\n\n"

        "Введите новую цену в юанях.\n"
        "Только число.",

    )

    await callback.answer()


# =========================================================
# НОВАЯ ЦЕНА
# =========================================================

@router.message(
    EditItemStates.waiting_new_price,
    F.text,
)
async def edit_item_price(
    message: Message,
    state: FSMContext,
):

    raw = (
        message.text
        .strip()
        .replace(",", ".")
    )

    try:

        price = float(raw)

        if price <= 0:
            raise ValueError

    except ValueError:

        await message.answer(
            "⚠️ Нужно отправить число.\n\n"
            "Например: <b>47</b> или <b>47.5</b>"
        )

        return

    data = await state.get_data()

    item_id = data.get(
        "item_id"
    )

    if not item_id:

        await state.clear()

        await message.answer(
            "⚠️ Не удалось определить товар.",
            reply_markup=main_menu,
        )

        return

    item = await db.get_cart_item(
        item_id,
        message.from_user.id,
    )

    if not item:

        await state.clear()

        await message.answer(
            "⚠️ Товар не найден.",
            reply_markup=main_menu,
        )

        return

    product_cost = calc_cost(
        price,
        item["quantity"],
    )

    shipping = (
        item["shipping_rub"]
        or 0
    )

    if item["weight_estimated"]:

        new_cost = round(
            product_cost,
            2,
        )

    else:

        new_cost = round(
            product_cost + shipping,
            2,
        )

    # Удаляем старый товар
    await db.delete_cart_item(
        item["id"],
        message.from_user.id,
    )

    # Создаём обновлённый
    await db.add_cart_item(

        user_id=(
            message.from_user.id
        ),

        link=item["link"],

        photo_id=item["photo_id"],

        price_yuan=price,

        quantity=item["quantity"],

        size=item["size"],

        weight_kg=item["weight_kg"],

        weight_min_kg=(
            item["weight_min_kg"]
        ),

        weight_max_kg=(
            item["weight_max_kg"]
        ),

        weight_estimated=bool(
            item["weight_estimated"]
        ),

        shipping_rub=shipping,

        cost_rub=new_cost,
    )

    total = await db.get_cart_total(
        message.from_user.id
    )

    await state.clear()

    await message.answer(

        "✅ <b>Цена обновлена.</b>\n\n"

        f"Новая стоимость товара: "
        f"<b>{product_cost:.0f} ₽</b>\n\n"

        f"Общая сумма товаров: "
        f"<b>{total:.0f} ₽</b>",

        reply_markup=main_menu,
    )


# =========================================================
# ОЧИСТКА КОРЗИНЫ
# =========================================================

@router.callback_query(
    F.data == "clear_cart"
)
async def clear_cart_cb(
    callback: CallbackQuery,
):

    await db.clear_cart(
        callback.from_user.id
    )

    await callback.message.answer(
        "🗑 <b>Корзина очищена.</b>",
        reply_markup=main_menu,
    )

    await callback.answer()


# =========================================================
# ОТПРАВКА МЕНЕДЖЕРУ
# =========================================================

@router.callback_query(
    F.data == "send_to_manager"
)
async def send_to_manager(
    callback: CallbackQuery,
    bot: Bot,
):

    user_id = callback.from_user.id

    items = await db.get_cart(
        user_id
    )

    if not items:

        await callback.answer(
            "Корзина пуста.",
            show_alert=True,
        )

        return

    order_id = await db.create_order_from_cart(
        user_id
    )

    if not order_id:

        await callback.answer(
            "Не удалось создать заявку.",
            show_alert=True,
        )

        return

    order = await db.get_order(
        order_id
    )

    order_items = await db.get_order_items(
        order_id
    )

    user = callback.from_user

    header = (

        f"📦 <b>Новая заявка №{order_id}</b>\n\n"

        f"👤 Клиент: "
        f"{user.full_name}\n"

        f"Telegram: "
        f"@{user.username or '—'}\n"

        f"ID: <code>{user.id}</code>\n\n"
    )

    body = "\n\n".join(
        _item_text(item)
        for item in order_items
    )

    footer = (

        f"\n\n💰 <b>Итого товаров:</b> "
        f"{order['total_rub']:.0f} ₽\n\n"

        "🚚 Доставка: "
        "<b>уточняется после "
        "фактического взвешивания</b>\n\n"

        f"📌 Статус: "
        f"<b>{order['status']}</b>"
    )

    if MANAGER_CHAT_ID:

        await bot.send_message(

            MANAGER_CHAT_ID,

            header
            + body
            + footer,

            reply_markup=admin_status_kb(
                order_id,
                weight_set=bool(
                    order["weight_set"]
                ),
            ),
        )

    await callback.message.answer(

        f"✅ <b>Заявка №{order_id} "
        "отправлена менеджеру!</b>\n\n"

        f"💰 Сумма товаров: "
        f"<b>{order['total_rub']:.0f} ₽</b>\n\n"

        "🚚 Доставка будет рассчитана "
        "после фактического взвешивания.",

        reply_markup=main_menu,
    )

    await callback.answer()
