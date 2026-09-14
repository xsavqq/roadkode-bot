from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
from config import calc_cost, EXCHANGE_RATE, MARKUP_PERCENT
from states import OrderStates
from keyboards import after_item_added_kb, main_menu, skip_kb

router = Router()


async def start_new_item(target, state: FSMContext):
    """target — Message или CallbackQuery, откуда взять chat/answer."""
    await state.set_state(OrderStates.waiting_link)
    text = "🔗 Отправьте ссылку на товар.\n\nЕсли ссылки нет или вы не умеете её копировать — отправьте символ -"
    if isinstance(target, CallbackQuery):
        await target.message.answer(text, reply_markup=skip_kb)
        await target.answer()
    else:
        await target.answer(text, reply_markup=skip_kb)


@router.message(F.text == "🛒 Новый заказ")
async def new_order(message: Message, state: FSMContext):
    await start_new_item(message, state)


@router.callback_query(F.data == "add_item")
async def add_item_cb(callback: CallbackQuery, state: FSMContext):
    await start_new_item(callback, state)


# ---------- Шаг 1: ссылка / фото / "-" ----------
@router.message(OrderStates.waiting_link, F.photo)
async def got_link_photo(message: Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    await state.update_data(link=None, photo_id=photo_id)
    await ask_price(message, state)


@router.message(OrderStates.waiting_link, F.text)
async def got_link_text(message: Message, state: FSMContext):
    link = None if message.text.strip() == "-" else message.text.strip()
    await state.update_data(link=link, photo_id=None)
    await ask_price(message, state)


async def ask_price(message: Message, state: FSMContext):
    await state.set_state(OrderStates.waiting_price)
    await message.answer("💴 Введите цену в юанях, только число.")


# ---------- Шаг 2: цена ----------
@router.message(OrderStates.waiting_price, F.text)
async def got_price(message: Message, state: FSMContext):
    raw = message.text.strip().replace(",", ".")
    try:
        price = float(raw)
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Нужно отправить число, например: 47 или 47.5")
        return
    await state.update_data(price_yuan=price)
    await state.set_state(OrderStates.waiting_qty)
    await message.answer("🔢 Введите количество, только целое число.")


# ---------- Шаг 3: количество ----------
@router.message(OrderStates.waiting_qty, F.text)
async def got_qty(message: Message, state: FSMContext):
    raw = message.text.strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer("⚠️ Нужно отправить целое число, например: 1 или 2")
        return
    await state.update_data(quantity=int(raw))
    await state.set_state(OrderStates.waiting_size)
    await message.answer(
        "📏 Введите размер.\nЕсли размера нет — отправьте -",
        reply_markup=skip_kb,
    )


# ---------- Шаг 4: размер -> считаем и сохраняем ----------
@router.message(OrderStates.waiting_size, F.text)
async def got_size(message: Message, state: FSMContext):
    size = None if message.text.strip() == "-" else message.text.strip()
    data = await state.get_data()

    cost = calc_cost(data["price_yuan"], data["quantity"])

    await db.add_cart_item(
        user_id=message.from_user.id,
        link=data.get("link"),
        photo_id=data.get("photo_id"),
        price_yuan=data["price_yuan"],
        quantity=data["quantity"],
        size=size,
        cost_rub=cost,
    )

    cart = await db.get_cart(message.from_user.id)
    total = await db.get_cart_total(message.from_user.id)

    await message.answer(
        f"✅ Товар №{len(cart)} добавлен\n\n"
        f"Стоимость: {cost:.0f} ₽\n"
        f"Общая сумма: {total:.0f} ₽",
        reply_markup=after_item_added_kb(),
    )
    # возвращаем обычную клавиатуру меню (skip_kb был one_time)
    await message.answer("Выберите действие.", reply_markup=main_menu)
    await state.clear()
