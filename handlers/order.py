from io import BytesIO

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
from ai_vision import estimate_weight_from_image
from config import calc_cost, yuan_rate_text
from states import OrderStates
from keyboards import after_item_added_kb, main_menu, skip_kb


router = Router()


async def start_new_item(
    target,
    state: FSMContext,
):
    await state.clear()

    await state.set_state(
        OrderStates.waiting_link
    )

    rate_text = yuan_rate_text()

    link_text = (
        "🔗 Отправьте ссылку на товар.\n\n"
        "Если ссылки нет или вы не умеете её копировать — "
        "отправьте символ -"
    )

    if isinstance(target, CallbackQuery):
        await target.message.answer(
            rate_text
        )

        await target.message.answer(
            link_text
        )

        await target.answer()

    else:
        await target.answer(
            rate_text
        )

        await target.answer(
            link_text
        )


@router.message(
    F.text == "🛒 Новый заказ"
)
async def new_order(
    message: Message,
    state: FSMContext,
):
    await start_new_item(
        message,
        state,
    )


@router.callback_query(
    F.data == "add_item"
)
async def add_item_cb(
    callback: CallbackQuery,
    state: FSMContext,
):
    await start_new_item(
        callback,
        state,
    )


@router.message(
    OrderStates.waiting_link,
    F.text,
)
async def got_link_text(
    message: Message,
    state: FSMContext,
):
    text = message.text.strip()

    link = (
        None
        if text == "-"
        else text
    )

    await state.update_data(
        link=link,
        photo_id=None,
        weight_estimated=False,
        estimated_weight_min=None,
        estimated_weight_max=None,
        estimated_weight_mid=None,
        estimated_product_type=None,
        estimated_confidence=None,
        estimated_note=None,
    )

    await state.set_state(
        OrderStates.waiting_photo
    )

    await message.answer(
        "📷 Отправьте фото или скрин товара."
    )


@router.message(
    OrderStates.waiting_link,
    F.photo,
)
async def photo_before_link(
    message: Message,
):
    await message.answer(
        "🔗 Сначала отправьте ссылку на товар.\n\n"
        "Если ссылки нет или вы не умеете её копировать — "
        "отправьте символ -"
    )


@router.message(
    OrderStates.waiting_photo,
    F.photo,
)
async def got_photo(
    message: Message,
    state: FSMContext,
    bot: Bot,
):
    photo_id = message.photo[-1].file_id

    await state.update_data(
        photo_id=photo_id,
        weight_estimated=False,
        estimated_weight_min=None,
        estimated_weight_max=None,
        estimated_weight_mid=None,
        estimated_product_type=None,
        estimated_confidence=None,
        estimated_note=None,
    )

    await message.answer(
        "🤖 Анализирую фото товара..."
    )

    try:
        telegram_file = await bot.get_file(
            photo_id
        )

        photo_buffer = BytesIO()

        await bot.download(
            telegram_file,
            destination=photo_buffer,
        )

        photo_bytes = photo_buffer.getvalue()

        if not photo_bytes:
            raise ValueError(
                "Не удалось скачать изображение"
            )

        result = await estimate_weight_from_image(
            photo_bytes
        )

        min_weight = float(
            result["min_kg"]
        )

        max_weight = float(
            result["max_kg"]
        )

        if min_weight <= 0 or max_weight <= 0:
            raise ValueError(
                "AI вернул некорректный вес"
            )

        if min_weight > max_weight:
            min_weight, max_weight = (
                max_weight,
                min_weight,
            )

        mid_weight = round(
            (min_weight + max_weight) / 2,
            3,
        )

        await state.update_data(
            weight_estimated=True,
            estimated_weight_min=min_weight,
            estimated_weight_max=max_weight,
            estimated_weight_mid=mid_weight,
            estimated_product_type=result.get(
                "product_type"
            ),
            estimated_confidence=result.get(
                "confidence"
            ),
            estimated_note=result.get(
                "note"
            ),
        )

        await message.answer(
            "🤖 Фото проанализировано.\n\n"
            f"Примерный вес 1 шт.: "
            f"{min_weight:.2f}–{max_weight:.2f} кг\n\n"
            "⚠️ Вес ориентировочный и нужен "
            "только для предварительной оценки.\n\n"
            "🚚 Доставка сейчас НЕ включается "
            "в сумму к оплате.\n"
            "Фактическая доставка будет уточнена "
            "после взвешивания.\n\n"
            "💴 Введите цену в юанях, только число."
        )

        await state.set_state(
            OrderStates.waiting_price
        )

    except Exception as exc:
        print(
            "AI WEIGHT ESTIMATION ERROR:",
            repr(exc),
            flush=True,
        )

        await state.update_data(
            weight_estimated=False,
            estimated_weight_min=None,
            estimated_weight_max=None,
            estimated_weight_mid=None,
        )

        await message.answer(
            "⚠️ Не удалось автоматически определить "
            "примерный вес по фото.\n\n"
            "Это не мешает оформить заказ.\n"
            "Фактический вес и доставка будут уточнены "
            "после взвешивания.\n\n"
            "💴 Введите цену в юанях, только число."
        )

        await state.set_state(
            OrderStates.waiting_price
        )


@router.message(
    OrderStates.waiting_photo,
    F.text,
)
async def waiting_photo_text(
    message: Message,
):
    await message.answer(
        "📷 Отправьте фото или скрин товара."
    )


@router.message(
    OrderStates.waiting_price,
    F.text,
)
async def got_price(
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
            "Например:\n"
            "47\n"
            "47.5"
        )

        return

    await state.update_data(
        price_yuan=price
    )

    await state.set_state(
        OrderStates.waiting_qty
    )

    await message.answer(
        "🔢 Введите количество, только целое число."
    )


@router.message(
    OrderStates.waiting_qty,
    F.text,
)
async def got_qty(
    message: Message,
    state: FSMContext,
):
    raw = message.text.strip()

    if (
        not raw.isdigit()
        or int(raw) <= 0
    ):
        await message.answer(
            "⚠️ Нужно отправить целое число.\n\n"
            "Например: 1 или 2"
        )

        return

    await state.update_data(
        quantity=int(raw)
    )

    await state.set_state(
        OrderStates.waiting_size
    )

    await message.answer(
        "📏 Введите размер.\n"
        "Если размера нет — отправьте -",
        reply_markup=skip_kb,
    )


@router.message(
    OrderStates.waiting_size,
    F.text,
)
async def got_size(
    message: Message,
    state: FSMContext,
):
    size_text = message.text.strip()

    size = (
        None
        if size_text == "-"
        else size_text
    )

    await state.update_data(
        size=size
    )

    await save_item(
        message=message,
        state=state,
    )


async def save_item(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    price_yuan = data["price_yuan"]
    quantity = data["quantity"]

    cost = calc_cost(
        price_yuan,
        quantity,
    )

    weight_estimated = bool(
        data.get("weight_estimated")
    )

    min_weight = data.get(
        "estimated_weight_min"
    )

    max_weight = data.get(
        "estimated_weight_max"
    )

    mid_weight = data.get(
        "estimated_weight_mid"
    )

    total_item_cost = round(
        cost,
        2,
    )

    await db.add_cart_item(
        user_id=message.from_user.id,
        link=data.get("link"),
        photo_id=data.get("photo_id"),
        price_yuan=price_yuan,
        quantity=quantity,
        size=data.get("size"),
        weight_kg=(
            mid_weight
            if weight_estimated
            else None
        ),
        weight_min_kg=(
            min_weight
            if weight_estimated
            else None
        ),
        weight_max_kg=(
            max_weight
            if weight_estimated
            else None
        ),
        weight_estimated=weight_estimated,
        shipping_rub=0,
        cost_rub=total_item_cost,
    )

    cart = await db.get_cart(
        message.from_user.id
    )

    total = await db.get_cart_total(
        message.from_user.id
    )

    if (
        weight_estimated
        and min_weight is not None
        and max_weight is not None
    ):
        weight_block = (
            f"🤖 Примерный вес 1 шт.: "
            f"{min_weight:.2f}–{max_weight:.2f} кг\n"
            "⚠️ Вес ориентировочный\n"
            "🚚 Доставка: уточняется после "
            "фактического взвешивания"
        )

    else:
        weight_block = (
            "⚖️ Вес: будет уточнён после "
            "фактического взвешивания\n"
            "🚚 Доставка: уточняется после взвешивания"
        )

    await message.answer(
        f"✅ Товар №{len(cart)} добавлен\n\n"
        f"Стоимость товара: "
        f"{cost:.0f} ₽\n\n"
        f"{weight_block}\n\n"
        f"💰 К оплате сейчас: "
        f"{total_item_cost:.0f} ₽\n\n"
        f"Общая сумма заказа: "
        f"{total:.0f} ₽",
        reply_markup=after_item_added_kb(),
    )

    await message.answer(
        "Выберите действие.",
        reply_markup=main_menu,
    )

    await state.clear()
