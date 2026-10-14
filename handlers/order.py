Фfrom io import BytesIO

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
from ai_vision import estimate_weight_from_image
from config import calc_cost, yuan_rate_text
from screens import drop_reply_kb, send_step
from states import OrderStates

from keyboards import (
    ORDER_CATEGORIES,
    order_category_kb,
    order_subcategory_kb,
    after_item_added_kb,
    main_menu,
    cancel_kb,
    skip_cancel_kb,
)


router = Router()


# =========================================================
# ОТМЕНА ОФОРМЛЕНИЯ
# =========================================================

@router.message(F.text == "❌ Отмена")
async def cancel_order(
    message: Message,
    state: FSMContext,
):
    await state.clear()

    await drop_reply_kb(message)

    await message.answer(
        "❌ Оформление заказа отменено.\n\n"
        "Выберите действие.",
        reply_markup=main_menu,
    )


# =========================================================
# НАЧАЛО ДОБАВЛЕНИЯ ТОВАРА
# =========================================================

TOTAL_STEPS = 6

CATEGORY_CAPTION = (
    "<b>[ НОВЫЙ ЗАКАЗ ]</b>\n\n"
    f"ШАГ 1 ИЗ {TOTAL_STEPS} · выберите категорию товара\n\n"
    "категории ниже ⤵"
)


async def start_new_item(
    target,
    state: FSMContext,
):
    await state.clear()

    await state.set_state(
        OrderStates.choosing_category
    )

    message = (
        target.message
        if isinstance(target, CallbackQuery)
        else target
    )

    await message.answer(
        yuan_rate_text()
    )

    await send_step(
        message,
        "category",
        CATEGORY_CAPTION,
        order_category_kb(),
    )

    if isinstance(target, CallbackQuery):
        await target.answer()


async def _edit_step(
    callback: CallbackQuery,
    text: str,
    kb,
):
    """Меняет подпись/текст сообщения с кнопками категорий."""

    try:
        if callback.message.photo:
            await callback.message.edit_caption(
                caption=text,
                reply_markup=kb,
            )
        else:
            await callback.message.edit_text(
                text,
                reply_markup=kb,
            )
    except Exception:
        await callback.message.answer(
            text,
            reply_markup=kb,
        )


async def ask_link(message: Message):
    await send_step(
        message,
        "link",
        "<b>[ НОВЫЙ ЗАКАЗ ]</b>\n\n"
        f"ШАГ 2 ИЗ {TOTAL_STEPS} · отправьте ссылку на товар\n"
        "с Poizon, Taobao, 1688 и других площадок\n\n"
        "Нет ссылки или не умеете её копировать — "
        "отправьте -",
        cancel_kb,
    )


# =========================================================
# ШАГ 1: КАТЕГОРИЯ / ПОДКАТЕГОРИЯ
# =========================================================

@router.callback_query(
    OrderStates.choosing_category,
    F.data == "cat:back",
)
async def category_back(callback: CallbackQuery):
    await _edit_step(
        callback,
        CATEGORY_CAPTION,
        order_category_kb(),
    )
    await callback.answer()


@router.callback_query(
    OrderStates.choosing_category,
    F.data.startswith("cat:"),
)
async def category_chosen(
    callback: CallbackQuery,
    state: FSMContext,
):
    try:
        index = int(callback.data.split(":")[1])
        title, subs = ORDER_CATEGORIES[index]
    except (ValueError, IndexError):
        await callback.answer()
        return

    if subs:
        await _edit_step(
            callback,
            "<b>[ НОВЫЙ ЗАКАЗ ]</b>\n\n"
            f"ШАГ 1 ИЗ {TOTAL_STEPS} · {title}\n\n"
            "уточните, что именно ⤵",
            order_subcategory_kb(index),
        )
        await callback.answer()
        return

    await _category_done(callback, state, title)


@router.callback_query(
    OrderStates.choosing_category,
    F.data.startswith("sub:"),
)
async def subcategory_chosen(
    callback: CallbackQuery,
    state: FSMContext,
):
    try:
        _, i, j = callback.data.split(":")
        title, subs = ORDER_CATEGORIES[int(i)]
        label = f"{title} / {subs[int(j)]}"
    except (ValueError, IndexError):
        await callback.answer()
        return

    await _category_done(callback, state, label)


async def _category_done(
    callback: CallbackQuery,
    state: FSMContext,
    label: str,
):
    await state.update_data(category=label)

    await state.set_state(OrderStates.waiting_link)

    await _edit_step(
        callback,
        "<b>[ НОВЫЙ ЗАКАЗ ]</b>\n\n"
        f"товар: {label}",
        None,
    )

    await ask_link(callback.message)

    await callback.answer()


# Старые кнопки категорий (после перезапуска бота состояние
# сбрасывается) — просто начинаем заказ заново.
@router.callback_query(F.data.startswith(("cat:", "sub:")))
async def category_stale(
    callback: CallbackQuery,
    state: FSMContext,
):
    await start_new_item(callback, state)


# =========================================================
# КНОПКА «НОВЫЙ ЗАКАЗ»
# =========================================================

@router.message(F.text == "🛒 Новый заказ")
async def new_order(
    message: Message,
    state: FSMContext,
):
    await start_new_item(
        message,
        state,
    )


# =========================================================
# КНОПКА «ДОБАВИТЬ ТОВАР»
# =========================================================

@router.callback_query(F.data == "add_item")
async def add_item_cb(
    callback: CallbackQuery,
    state: FSMContext,
):
    await start_new_item(
        callback,
        state,
    )


# =========================================================
# ПОЛУЧИЛИ ССЫЛКУ / «-»
# =========================================================

@router.message(
    OrderStates.waiting_link,
    F.text,
)
async def got_link_text(
    message: Message,
    state: FSMContext,
):
    text = message.text.strip()

    if text == "-":
        link = None
    else:
        link = text

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
        OrderStates.waiting_size
    )

    await ask_size(message)


async def ask_size(message: Message):
    await send_step(
        message,
        "size",
        "<b>[ НОВЫЙ ЗАКАЗ ]</b>\n\n"
        f"ШАГ 3 ИЗ {TOTAL_STEPS} · укажите размер\n"
        "например: 42, M или -",
        skip_cancel_kb,
    )


# =========================================================
# ЕСЛИ ВМЕСТО ССЫЛКИ СРАЗУ ОТПРАВИЛИ ФОТО
# =========================================================

@router.message(
    OrderStates.waiting_link,
    F.photo,
)
async def photo_before_link(
    message: Message,
):
    await message.answer(
        "🔗 Сначала отправьте ссылку на товар.\n\n"
        "Фото можно будет приложить на последнем шаге.\n"
        "Нет ссылки — отправьте -",
        reply_markup=cancel_kb,
    )


# =========================================================
# ПОЛУЧИЛИ ФОТО
# =========================================================

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
    )

    await message.answer(
        "🤖 Анализирую фото товара...",
        reply_markup=cancel_kb,
    )

    try:

        # -------------------------------------------------
        # СКАЧИВАЕМ ФОТО ИЗ TELEGRAM
        # -------------------------------------------------

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

        # -------------------------------------------------
        # AI ОПРЕДЕЛЯЕТ ПРИМЕРНЫЙ ВЕС
        # -------------------------------------------------

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

        # -------------------------------------------------
        # ВАЖНО:
        # ЭТОТ ВЕС НЕ ДОБАВЛЯЕТСЯ В СУММУ К ОПЛАТЕ
        # -------------------------------------------------

        await message.answer(
            "🤖 Фото проанализировано.\n\n"

            f"Примерный вес 1 шт.: "
            f"{min_weight:.2f}–{max_weight:.2f} кг\n\n"

            "⚠️ Вес ориентировочный и нужен "
            "только для предварительной оценки.\n\n"

            "🚚 Доставка сейчас НЕ включается "
            "в сумму к оплате.\n"

            "Фактическая доставка будет уточнена "
            "после взвешивания.",
            reply_markup=cancel_kb,
        )

        await save_item(
            message,
            state,
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

            "Фактический вес и доставка будут "
            "уточнены после взвешивания.",
            reply_markup=cancel_kb,
        )

        await save_item(
            message,
            state,
        )


# =========================================================
# ЕСЛИ ВМЕСТО ФОТО ПРИСЛАЛИ ТЕКСТ
# =========================================================

@router.message(
    OrderStates.waiting_photo,
    F.text,
)
async def waiting_photo_text(
    message: Message,
    state: FSMContext,
):
    if message.text.strip().lower() in ("-", "нет", "no"):

        await state.update_data(
            photo_id=None,
            weight_estimated=False,
            estimated_weight_min=None,
            estimated_weight_max=None,
            estimated_weight_mid=None,
        )

        await save_item(
            message,
            state,
        )

        return

    await message.answer(
        "📷 Пришлите фото или скрин товара "
        "или напишите - чтобы пропустить.",
        reply_markup=skip_cancel_kb,
    )


# =========================================================
# ПОЛУЧИЛИ ЦЕНУ
# =========================================================

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
            "⚠️ Нужно отправить число, например: "
            "47 или 47.5",
            reply_markup=cancel_kb,
        )

        return

    await state.update_data(
        price_yuan=price
    )

    await state.set_state(
        OrderStates.waiting_qty
    )

    await message.answer(
        "<b>[ НОВЫЙ ЗАКАЗ ]</b>\n\n"
        f"ШАГ 5 ИЗ {TOTAL_STEPS} · количество\n"
        "только целое число, например: 1",
        reply_markup=cancel_kb,
    )


# =========================================================
# ПОЛУЧИЛИ КОЛИЧЕСТВО
# =========================================================

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
            "⚠️ Нужно отправить целое число, "
            "например: 1 или 2",
            reply_markup=cancel_kb,
        )

        return

    await state.update_data(
        quantity=int(raw)
    )

    await state.set_state(
        OrderStates.waiting_photo
    )

    await message.answer(
        "<b>[ НОВЫЙ ЗАКАЗ ]</b>\n\n"
        f"ШАГ 6 ИЗ {TOTAL_STEPS} · пришлите фото товара\n"
        "или напишите - чтобы пропустить",
        reply_markup=skip_cancel_kb,
    )


# =========================================================
# ПОЛУЧИЛИ РАЗМЕР
# =========================================================

@router.message(
    OrderStates.waiting_size,
    F.text,
)
async def got_size(
    message: Message,
    state: FSMContext,
):
    size = (
        None
        if message.text.strip() == "-"
        else message.text.strip()
    )

    await state.update_data(
        size=size
    )

    await state.set_state(
        OrderStates.waiting_price
    )

    await send_step(
        message,
        "price",
        "<b>[ НОВЫЙ ЗАКАЗ ]</b>\n\n"
        f"ШАГ 4 ИЗ {TOTAL_STEPS} · цена товара в юанях\n"
        "только число, например: 350",
        cancel_kb,
    )


# =========================================================
# СОХРАНЕНИЕ ТОВАРА В КОРЗИНУ
# =========================================================

async def save_item(
    message: Message,
    state: FSMContext,
):
    data = await state.get_data()

    price_yuan = data["price_yuan"]
    quantity = data["quantity"]

    # -------------------------------------------------
    # СЧИТАЕМ ТОЛЬКО СТОИМОСТЬ ТОВАРА
    #
    # AI-ВЕС ЗДЕСЬ НЕ УЧАСТВУЕТ В СУММЕ
    # -------------------------------------------------

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

    await db.add_cart_item(
        user_id=message.from_user.id,

        link=data.get("link"),

        photo_id=data.get("photo_id"),

        price_yuan=price_yuan,

        quantity=quantity,

        size=" · ".join(
            part
            for part in (
                data.get("category"),
                data.get("size"),
            )
            if part
        ) or None,

        # AI-вес сохраняем для информации,
        # но shipping_rub = 0
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

        cost_rub=round(
            cost,
            2,
        ),
    )

    # -------------------------------------------------
    # ПОЛУЧАЕМ КОРЗИНУ
    # -------------------------------------------------

    cart = await db.get_cart(
        message.from_user.id
    )

    total = await db.get_cart_total(
        message.from_user.id
    )

    # -------------------------------------------------
    # ИНФОРМАЦИЯ О ВЕСЕ
    # -------------------------------------------------

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

            "🚚 Доставка: уточняется после "
            "взвешивания"
        )

    # -------------------------------------------------
    # ПОКАЗЫВАЕМ РЕЗУЛЬТАТ
    # -------------------------------------------------

    await message.answer(
        f"✅ Товар №{len(cart)} добавлен\n\n"

        f"Стоимость товара: "
        f"{cost:.0f} ₽\n\n"

        f"{weight_block}\n\n"

        f"💰 К оплате сейчас: "
        f"{cost:.0f} ₽\n\n"

        f"Общая сумма заказа: "
        f"{total:.0f} ₽",

        reply_markup=after_item_added_kb(),
    )

    # -------------------------------------------------
    # ВОЗВРАЩАЕМ ГЛАВНОЕ МЕНЮ
    # -------------------------------------------------

    await drop_reply_kb(message)

    await message.answer(
        "Выберите действие.",
        reply_markup=main_menu,
    )

    await state.clear()
