from io import BytesIO

from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
from config import calc_cost, calc_shipping, yuan_rate_text
from states import OrderStates
from keyboards import after_item_added_kb, main_menu, skip_kb
from ai_vision import estimate_weight_from_image

router = Router()


async def start_new_item(target, state: FSMContext):
    """target — Message или CallbackQuery, откуда взять chat/answer."""

    await state.set_state(OrderStates.waiting_link)

    rate_text = yuan_rate_text()

    link_text = (
        "🔗 Отправьте ссылку на товар.\n\n"
        "Или отправьте 📷 фото товара — я попробую "
        "примерно определить его вес.\n\n"
        "Если ссылки и фото нет — отправьте символ -"
    )

    if isinstance(target, CallbackQuery):
        await target.message.answer(rate_text)
        await target.message.answer(
            link_text,
            reply_markup=skip_kb
        )
        await target.answer()
    else:
        await target.answer(rate_text)
        await target.answer(
            link_text,
            reply_markup=skip_kb
        )


@router.message(F.text == "🛒 Новый заказ")
async def new_order(
    message: Message,
    state: FSMContext
):
    await start_new_item(message, state)


@router.callback_query(F.data == "add_item")
async def add_item_cb(
    callback: CallbackQuery,
    state: FSMContext
):
    await start_new_item(callback, state)


# =========================================================
# ШАГ 1: ССЫЛКА / ФОТО / "-"
# =========================================================

@router.message(
    OrderStates.waiting_link,
    F.photo
)
async def got_link_photo(
    message: Message,
    state: FSMContext,
    bot: Bot
):
    """
    Пользователь отправил фото.
    Скачиваем фото из Telegram и отправляем его в AI.
    AI возвращает примерный диапазон веса.
    """

    photo_id = message.photo[-1].file_id

    # Сохраняем Telegram photo_id
    await state.update_data(
        link=None,
        photo_id=photo_id
    )

    await message.answer(
        "🤖 Анализирую фото товара и пытаюсь "
        "определить примерный вес..."
    )

    try:
        # Получаем информацию о файле Telegram
        telegram_file = await bot.get_file(photo_id)

        # BytesIO — безопасный способ скачать файл
        # прямо в память, без создания временного файла.
        photo_buffer = BytesIO()

        await bot.download(
            telegram_file,
            destination=photo_buffer
        )

        photo_bytes = photo_buffer.getvalue()

        if not photo_bytes:
            raise ValueError(
                "Не удалось скачать изображение"
            )

        # Отправляем фото в AI
        estimate = await estimate_weight_from_image(
            photo_bytes
        )

        min_weight = estimate["min_kg"]
        max_weight = estimate["max_kg"]

        # Среднее значение используется ТОЛЬКО
        # технически для хранения.
        # В стоимость доставки оно НЕ попадает.
        mid_weight = round(
            (min_weight + max_weight) / 2,
            3
        )

        await state.update_data(
            estimated_weight_min=min_weight,
            estimated_weight_max=max_weight,
            estimated_weight_mid=mid_weight,
            weight_estimated=True,
            estimated_product_type=estimate.get(
                "product_type"
            ),
            estimated_confidence=estimate.get(
                "confidence"
            ),
            estimated_note=estimate.get(
                "note"
            ),
        )

        product_type = estimate.get(
            "product_type"
        ) or "товар"

        confidence = estimate.get(
            "confidence"
        ) or "low"

        confidence_text = {
            "high": "высокая",
            "medium": "средняя",
            "low": "низкая",
        }.get(
            confidence,
            "низкая"
        )

        note = estimate.get("note")

        text = (
            "🤖 Фото проанализировано!\n\n"
            f"📦 Товар: {product_type}\n"
            f"⚖️ Примерный вес: "
            f"{min_weight:.2f}–{max_weight:.2f} кг\n"
            f"🎯 Точность оценки: {confidence_text}\n"
        )

        if note:
            text += f"\n💡 {note}\n"

        text += (
            "\n⚠️ Это ориентировочный вес, "
            "а не точное взвешивание.\n\n"
            "🚚 ВАЖНО: примерный вес НЕ используется "
            "для расчёта доставки и НЕ добавляется "
            "в сумму к оплате сейчас.\n\n"
            "Фактическая доставка будет уточнена "
            "после взвешивания товара."
        )

        await message.answer(text)

    except Exception as e:
        # Не ломаем заказ, если AI временно недоступен.
        await state.update_data(
            weight_estimated=False,
            estimated_weight_min=None,
            estimated_weight_max=None,
            estimated_weight_mid=None,
        )

        await message.answer(
            "⚠️ Не удалось автоматически определить "
            "вес по фото.\n\n"
            "Ничего страшного — продолжайте оформление. "
            "Позже можно будет указать вес вручную."
        )

    await ask_price(
        message,
        state
    )


@router.message(
    OrderStates.waiting_link,
    F.text
)
async def got_link_text(
    message: Message,
    state: FSMContext
):
    link = (
        None
        if message.text.strip() == "-"
        else message.text.strip()
    )

    await state.update_data(
        link=link,
        photo_id=None,
        weight_estimated=False,
        estimated_weight_min=None,
        estimated_weight_max=None,
        estimated_weight_mid=None,
    )

    await ask_price(
        message,
        state
    )


async def ask_price(
    message: Message,
    state: FSMContext
):
    await state.set_state(
        OrderStates.waiting_price
    )

    await message.answer(
        "💴 Введите цену в юанях, только число."
    )


# =========================================================
# ШАГ 2: ЦЕНА
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
# ШАГ 3: КОЛИЧЕСТВО
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

    if not raw.isdigit() or int(raw) <= 0:
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
        reply_markup=skip_kb,
    )


# =========================================================
# ШАГ 4: РАЗМЕР
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

    # Если вес уже определён AI,
    # не просим пользователя вводить его вручную.
    if data.get("weight_estimated"):
        await save_ai_weight_item(
            message,
            state
        )
        return

    # Обычный сценарий — просим вес.
    await state.set_state(
        OrderStates.waiting_weight
    )

    await message.answer(
        "⚖️ Введите вес товара в кг "
        "(например: 0.5 или 1.2).\n"
        "Если вес неизвестен — отправьте -",
        reply_markup=skip_kb,
    )


# =========================================================
# AI-ВЕС: СОХРАНЕНИЕ ТОВАРА
# =========================================================

async def save_ai_weight_item(
    message: Message,
    state: FSMContext
):
    data = await state.get_data()

    cost = calc_cost(
        data["price_yuan"],
        data["quantity"]
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

    # ВАЖНО:
    # shipping = 0.
    #
    # Средний вес хранится только технически.
    # Он НЕ участвует в стоимости.
    shipping = 0

    total_item_cost = round(
        cost,
        2
    )

    await db.add_cart_item(
        user_id=message.from_user.id,
        link=data.get("link"),
        photo_id=data.get("photo_id"),
        price_yuan=data["price_yuan"],
        quantity=data["quantity"],
        size=data.get("size"),
        weight_kg=mid_weight,
        weight_min_kg=min_weight,
        weight_max_kg=max_weight,
        weight_estimated=1,
        shipping_rub=shipping,
        cost_rub=total_item_cost,
    )

    cart = await db.get_cart(
        message.from_user.id
    )

    total = await db.get_cart_total(
        message.from_user.id
    )

    await message.answer(
        f"✅ Товар №{len(cart)} добавлен\n\n"
        f"Стоимость товара: {cost:.0f} ₽\n"
        f"🤖 Примерный вес: "
        f"{min_weight:.2f}–{max_weight:.2f} кг\n"
        f"🚚 Доставка: уточняется после взвешивания\n\n"
        f"💰 Итого за товар к оплате сейчас: "
        f"{total_item_cost:.0f} ₽\n\n"
        f"Общая сумма заказа: "
        f"{total:.0f} ₽",
        reply_markup=after_item_added_kb(),
    )

    await message.answer(
        "Выберите действие.",
        reply_markup=main_menu
    )

    await state.clear()


# =========================================================
# ШАГ 5: РУЧНОЙ ВЕС
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

    data = await state.get_data()

    cost = calc_cost(
        data["price_yuan"],
        data["quantity"]
    )

    shipping = (
        calc_shipping(weight)
        if weight
        else 0
    )

    total_item_cost = round(
        cost + shipping,
        2
    )

    await db.add_cart_item(
        user_id=message.from_user.id,
        link=data.get("link"),
        photo_id=data.get("photo_id"),
        price_yuan=data["price_yuan"],
        quantity=data["quantity"],
        size=data.get("size"),
        weight_kg=weight,
        weight_min_kg=None,
        weight_max_kg=None,
        weight_estimated=0,
        shipping_rub=shipping,
        cost_rub=total_item_cost,
    )

    cart = await db.get_cart(
        message.from_user.id
    )

    total = await db.get_cart_total(
        message.from_user.id
    )

    if weight:
        weight_line = (
            f"🚚 Доставка ({weight:.2f} кг): "
            f"{shipping:.0f} ₽\n"
        )
    else:
        weight_line = (
            "🚚 Доставка: не рассчитана\n"
        )

    await message.answer(
        f"✅ Товар №{len(cart)} добавлен\n\n"
        f"Стоимость товара: {cost:.0f} ₽\n"
        f"{weight_line}"
        f"Итого за товар: "
        f"{total_item_cost:.0f} ₽\n\n"
        f"Общая сумма заказа: "
        f"{total:.0f} ₽",
        reply_markup=after_item_added_kb(),
    )

    await message.answer(
        "Выберите действие.",
        reply_markup=main_menu
    )

    await state.clear()
