from io import BytesIO

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db

from ai_vision import (
    estimate_weight_from_image
)

from config import (
    calc_cost,
    calc_shipping,
    yuan_rate_text
)

from states import OrderStates

from keyboards import (
    after_item_added_kb,
    main_menu,
    skip_kb
)


router = Router()


# =========================================================
# НАЧАЛО НОВОГО ТОВАРА
# =========================================================

async def start_new_item(
    target,
    state: FSMContext
):

    await state.set_state(
        OrderStates.waiting_link
    )

    rate_text = yuan_rate_text()

    instruction = (
        "🔗 Отправьте ссылку на товар "
        "или 📷 фото / скрин товара.\n\n"
        "Если ссылки и фото нет — "
        "отправьте символ -"
    )

    if isinstance(
        target,
        CallbackQuery
    ):

        await target.message.answer(
            rate_text
        )

        await target.message.answer(
            instruction
        )

        await target.answer()

    else:

        await target.answer(
            rate_text
        )

        await target.answer(
            instruction
        )


@router.message(
    F.text == "🛒 Новый заказ"
)
async def new_order(
    message: Message,
    state: FSMContext
):

    await start_new_item(
        message,
        state
    )


@router.callback_query(
    F.data == "add_item"
)
async def add_item_cb(
    callback: CallbackQuery,
    state: FSMContext
):

    await start_new_item(
        callback,
        state
    )


# =========================================================
# ФОТО
# =========================================================

@router.message(
    OrderStates.waiting_link,
    F.photo
)
async def got_photo(
    message: Message,
    state: FSMContext,
    bot: Bot
):

    photo_id = (
        message.photo[-1].file_id
    )

    await state.update_data(
        link=None,
        photo_id=photo_id,

        weight_estimated=False,

        estimated_weight_min=None,
        estimated_weight_max=None,
        estimated_weight_mid=None,
    )

    await message.answer(
        "🤖 Анализирую фото товара..."
    )

    try:

        telegram_file = (
            await bot.get_file(
                photo_id
            )
        )

        photo_buffer = BytesIO()

        await bot.download(
            telegram_file,
            destination=photo_buffer
        )

        photo_bytes = (
            photo_buffer.getvalue()
        )

        if not photo_bytes:
            raise ValueError(
                "Не удалось скачать изображение"
            )

        # Только один аргумент!
        result = (
            await estimate_weight_from_image(
                photo_bytes
            )
        )

        min_weight = result[
            "min_kg"
        ]

        max_weight = result[
            "max_kg"
        ]

        # Средний вес нужен только технически
        # для хранения. В оплату он НЕ попадает.
        mid_weight = round(
            (
                min_weight
                + max_weight
            ) / 2,
            3
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
            "Вес будет использован только "
            "как ориентир для менеджера.\n\n"
            "🚚 Примерная доставка НЕ будет "
            "добавлена в сумму к оплате."
        )

    except Exception as exc:

        print(
            "AI weight estimation error:",
            repr(exc)
        )

        await state.update_data(
            weight_estimated=False,

            estimated_weight_min=None,
            estimated_weight_max=None,
            estimated_weight_mid=None,
        )

        await message.answer(
            "⚠️ Не удалось автоматически "
            "определить вес по фото.\n\n"
            "Продолжаем оформление. "
            "Доставку менеджер уточнит "
            "после фактического взвешивания."
        )

    # После фото ВСЕГДА идём к цене.
    await state.set_state(
        OrderStates.waiting_price
    )

    await message.answer(
        "💴 Введите цену в юанях, только число."
    )


# =========================================================
# ССЫЛКА / "-"
# =========================================================

@router.message(
    OrderStates.waiting_link,
    F.text
)
async def got_link_text(
    message: Message,
    state: FSMContext
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
    )

    await state.set_state(
        OrderStates.waiting_price
    )

    await message.answer(
        "💴 Введите цену в юанях, только число."
    )


# =========================================================
# ЦЕНА
# =========================================================

@router.message(
    OrderStates.waiting_price,
    F.text
)
async def got_price(
    message: Message,
    state: FSMContext
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
            "⚠️ Нужно отправить число, "
            "например: 47 или 47.5"
        )

        return

    await state.update_data(
        price_yuan=price
    )

    await state.set_state(
        OrderStates.waiting_qty
    )

    await message.answer(
        "🔢 Введите количество, "
        "только целое число."
    )


# =========================================================
# КОЛИЧЕСТВО
# =========================================================

@router.message(
    OrderStates.waiting_qty,
    F.text
)
async def got_qty(
    message: Message,
    state: FSMContext
):

    raw = message.text.strip()

    if (
        not raw.isdigit()
        or int(raw) <= 0
    ):

        await message.answer(
            "⚠️ Нужно отправить целое число, "
            "например: 1 или 2"
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
        reply_markup=skip_kb
    )


# =========================================================
# РАЗМЕР
# =========================================================

@router.message(
    OrderStates.waiting_size,
    F.text
)
async def got_size(
    message: Message,
    state: FSMContext
):

    size = (
        None
        if message.text.strip() == "-"
        else message.text.strip()
    )

    await state.update_data(
        size=size
    )

    data = await state.get_data()

    # =====================================================
    # ЕСЛИ БЫЛО ФОТО
    # =====================================================

    if data.get(
        "weight_estimated"
    ):

        await save_item(
            message,
            state,

            weight=data.get(
                "estimated_weight_mid"
            ),

            shipping=0,

            weight_estimated=True
        )

        return

    # =====================================================
    # ЕСЛИ БЫЛА ССЫЛКА
    # =====================================================

    await state.set_state(
        OrderStates.waiting_weight
    )

    await message.answer(
        "⚖️ Введите вес товара в кг "
        "(например: 0.5 или 1.2).\n"
        "Если вес неизвестен — отправьте -",
        reply_markup=skip_kb
    )


# =========================================================
# РУЧНОЙ ВЕС
# =========================================================

@router.message(
    OrderStates.waiting_weight,
    F.text
)
async def got_weight(
    message: Message,
    state: FSMContext
):

    raw = (
        message.text
        .strip()
        .replace(",", ".")
    )

    if raw == "-":

        weight = None

    else:

        try:

            weight = float(raw)

            if weight <= 0:
                raise ValueError

        except ValueError:

            await message.answer(
                "⚠️ Нужно отправить число, "
                "например: 0.5 или 1.2, либо -"
            )

            return

    shipping = (
        calc_shipping(weight)
        if weight
        else 0
    )

    await save_item(
        message,
        state,

        weight=weight,

        shipping=shipping,

        weight_estimated=False
    )


# =========================================================
# СОХРАНЕНИЕ
# =========================================================

async def save_item(
    message: Message,
    state: FSMContext,
    weight,
    shipping: float,
    weight_estimated: bool
):

    data = await state.get_data()

    cost = calc_cost(
        data["price_yuan"],
        data["quantity"]
    )

    # КРИТИЧЕСКИ ВАЖНО:
    #
    # AI-вес НЕ добавляет доставку.
    #
    if weight_estimated:

        total_item_cost = round(
            cost,
            2
        )

        shipping_to_save = 0

    else:

        total_item_cost = round(
            cost + shipping,
            2
        )

        shipping_to_save = shipping

    await db.add_cart_item(
        user_id=message.from_user.id,

        link=data.get(
            "link"
        ),

        photo_id=data.get(
            "photo_id"
        ),

        price_yuan=data[
            "price_yuan"
        ],

        quantity=data[
            "quantity"
        ],

        size=data.get(
            "size"
        ),

        weight_kg=weight,

        weight_min_kg=(
            data.get(
                "estimated_weight_min"
            )
            if weight_estimated
            else None
        ),

        weight_max_kg=(
            data.get(
                "estimated_weight_max"
            )
            if weight_estimated
            else None
        ),

        weight_estimated=weight_estimated,

        shipping_rub=shipping_to_save,

        cost_rub=total_item_cost,
    )

    cart = await db.get_cart(
        message.from_user.id
    )

    total = await db.get_cart_total(
        message.from_user.id
    )

    # =====================================================
    # AI-ВЕС
    # =====================================================

    if weight_estimated:

        min_weight = data.get(
            "estimated_weight_min"
        )

        max_weight = data.get(
            "estimated_weight_max"
        )

        weight_block = (
            f"🤖 Примерный вес 1 шт.: "
            f"{min_weight:.2f}–"
            f"{max_weight:.2f} кг\n"
            "🚚 Доставка: уточняется после "
            "фактического взвешивания"
        )

    # =====================================================
    # РУЧНОЙ ВЕС
    # =====================================================

    elif weight:

        weight_block = (
            f"⚖️ Вес: {weight:.2f} кг\n"
            f"🚚 Доставка: "
            f"{shipping:.0f} ₽"
        )

    else:

        weight_block = (
            "⚖️ Вес: не указан\n"
            "🚚 Доставка: уточняется "
            "после взвешивания"
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
        reply_markup=after_item_added_kb()
    )

    await message.answer(
        "Выберите действие.",
        reply_markup=main_menu
    )

    await state.clear()
