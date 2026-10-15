from urllib.parse import quote

from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

import database as db

from config import (
    BOT_NAME,
    EXCHANGE_RATE,
    MANAGER_USERNAME,
    MARKUP_PERCENT,
    PRICE_PER_KG,
    REFERRAL_BONUS_PER_KG,
    calc_breakdown,
)

from handlers.cabinet import build_ref_text, orders_text
from handlers.order import start_new_item
from keyboards import (
    STATUS_OPTIONS,
    assortment_kb,
    back_kb,
    calc_result_kb,
)
from screens import send_header, send_home
from states import CalcStates


router = Router()


def _rub(value: float) -> str:
    """12345.6 -> '12 346 ₽'"""
    return f"{value:,.0f}".replace(",", " ") + " ₽"


# =========================================================
# ГЛАВНЫЙ ЭКРАН / ВОЗВРАТ В МЕНЮ
# =========================================================

@router.callback_query(F.data == "menu:home")
async def menu_home(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.clear()
    await send_home(callback.message)
    await callback.answer()


# =========================================================
# СДЕЛАТЬ ЗАКАЗ  (тот же сценарий, что и раньше)
# =========================================================

@router.callback_query(F.data == "menu:order")
async def menu_order(
    callback: CallbackQuery,
    state: FSMContext,
):
    await start_new_item(callback, state)


# =========================================================
# МОИ ЗАКАЗЫ
# =========================================================

@router.callback_query(F.data == "menu:track")
async def menu_track(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.clear()

    await send_header(callback.message, "orders")

    text = await orders_text(callback.from_user.id)

    await callback.message.answer(
        "<b>[ МОИ ЗАКАЗЫ ]</b>\n\n" + text,
        reply_markup=back_kb(),
    )

    await callback.answer()


# =========================================================
# РЕФЕРАЛКА
# =========================================================

@router.callback_query(F.data == "menu:ref")
async def menu_ref(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
):
    await state.clear()

    await send_header(callback.message, "ref")

    text, ref_link = await build_ref_text(
        callback.from_user.id,
        bot,
    )

    share_url = (
        "https://t.me/share/url?url="
        + quote(ref_link, safe="")
        + "&text="
        + quote(
            f"Заказывай товары из Китая в {BOT_NAME}",
            safe="",
        )
    )

    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📤 Поделиться",
                    url=share_url,
                ),
                InlineKeyboardButton(
                    text="🎁 Мои бонусы",
                    callback_data="menu:bonus",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏠 В меню",
                    callback_data="menu:home",
                )
            ],
        ]
    )

    await callback.message.answer(
        text,
        reply_markup=kb,
        disable_web_page_preview=True,
    )

    await callback.answer()


# =========================================================
# БОНУСЫ
# =========================================================

@router.callback_query(F.data == "menu:bonus")
async def menu_bonus(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.clear()

    await send_header(callback.message, "bonus")

    stats = await db.get_referral_stats(callback.from_user.id)

    await callback.message.answer(
        "🎁 <b>[ БОНУСЫ ]</b>\n\n"
        f"💰 Баланс: <b>{stats['balance_rub']:.0f} ₽</b>\n"
        f"👥 Приглашено друзей: {stats['referrals_count']}\n\n"
        f"За каждый кг заказа друга вам начисляется "
        f"{REFERRAL_BONUS_PER_KG:.0f} ₽ (после взвешивания на складе). "
        "Баланс менеджер учитывает как скидку на ваш следующий заказ.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="👥 Пригласить друга",
                        callback_data="menu:ref",
                    ),
                    InlineKeyboardButton(
                        text="🏠 В меню",
                        callback_data="menu:home",
                    ),
                ]
            ]
        ),
    )

    await callback.answer()


# =========================================================
# КАЛЬКУЛЯТОР
# =========================================================

CALC_PRICE_TEXT = (
    "🧮 <b>[ КАЛЬКУЛЯТОР ]</b>\n\n"
    "💴 Отправьте цену товара в юанях — только число.\n"
    "Например: <b>129</b> или <b>47.5</b>\n\n"
    f"Курс сейчас: {EXCHANGE_RATE:.2f} ₽ за ¥"
)

CALC_WEIGHT_TEXT = (
    "⚖️ <b>Теперь вес одной единицы товара в кг.</b>\n"
    "Например: <b>0.8</b>\n\n"
    "Ориентиры (примерно):\n"
    "• футболка — 0.3 кг\n"
    "• худи — 0.8 кг\n"
    "• кроссовки — 1.2 кг\n"
    "• куртка — 1.5 кг\n\n"
    "Не знаете вес — отправьте <b>-</b>, "
    "посчитаю без доставки."
)


@router.callback_query(F.data == "menu:calc")
async def calc_start(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.clear()

    await send_header(callback.message, "calc")
    await state.set_state(CalcStates.waiting_price)

    await callback.message.answer(
        CALC_PRICE_TEXT,
        reply_markup=back_kb(),
    )

    await callback.answer()


@router.message(CalcStates.waiting_price, F.text)
async def calc_price(
    message: Message,
    state: FSMContext,
):
    raw = message.text.strip().replace(",", ".")

    try:
        price = float(raw)

        if price <= 0 or price > 1_000_000:
            raise ValueError

    except ValueError:
        await message.answer(
            "⚠️ Нужно отправить число.\n\n"
            "Например: <b>129</b> или <b>47.5</b>",
            reply_markup=back_kb(),
        )
        return

    await state.update_data(price_yuan=price)
    await state.set_state(CalcStates.waiting_weight)

    await message.answer(
        CALC_WEIGHT_TEXT,
        reply_markup=back_kb(),
    )


@router.message(CalcStates.waiting_weight, F.text)
async def calc_weight(
    message: Message,
    state: FSMContext,
):
    raw = message.text.strip().replace(",", ".")

    weight = None

    if raw != "-":

        try:
            weight = float(raw)

            if weight <= 0 or weight > 1000:
                raise ValueError

        except ValueError:
            await message.answer(
                "⚠️ Нужно отправить число в кг, например "
                "<b>0.8</b>, или <b>-</b> чтобы пропустить.",
                reply_markup=back_kb(),
            )
            return

    data = await state.get_data()
    price = data["price_yuan"]

    r = calc_breakdown(price, weight)

    lines = [
        "🧮 <b>[ РАСЧЁТ СТОИМОСТИ ]</b>\n",

        f"💴 Цена: {price:g} ¥ · курс {EXCHANGE_RATE:.2f} ₽",
        "━━━━━━━━━━━━━━",
        f"🛍 Товар по курсу: {_rub(r['goods'])}",
        f"💼 Комиссия ({MARKUP_PERCENT:g}%): {_rub(r['commission'])}",
    ]

    if weight:
        lines.append(
            f"🚚 Доставка ({weight:g} кг × {PRICE_PER_KG:.0f} ₽): "
            f"{_rub(r['shipping'])}"
        )
    else:
        lines.append("🚚 Доставка: считается по весу")

    lines += [
        "━━━━━━━━━━━━━━",
        f"💰 <b>ИТОГО: {_rub(r['total'])}</b>",
        "",
        "⚠️ Доставка не входит в оплату товара: её считаем "
        "по фактическому весу после взвешивания на складе. "
        "Расчёт предварительный.",
    ]

    await state.clear()

    await message.answer(
        "\n".join(lines),
        reply_markup=calc_result_kb(),
    )


# =========================================================
# АССОРТИМЕНТ  (с каких площадок выкупаем)
# =========================================================

ASSORTMENT_TEXT = (
    "<b>[ ОТКУДА ВЫКУПАЕМ ]</b>\n\n"
    "🛍 Taobao — огромный выбор на любой вкус по низким ценам\n"
    "📦 1688 — оптовые цены, удобно брать от партии\n"
    "👟 Poizon — оригинальная обувь и одежда с проверкой подлинности\n"
    "🏷 Pinduoduo — самые низкие цены на базовые вещи и мелочи\n"
    "📲 Weidian — магазины продавцов, часто редкие вещи\n\n"
    "Нет нужной площадки? Пришли ссылку или фото — менеджер подскажет.\n\n"
    "🛒 Оформить заказ — кнопка «Сделать заказ»."
)


@router.callback_query(F.data == "menu:assort")
async def menu_assortment(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.clear()

    await send_header(callback.message, "assort")

    await callback.message.answer(
        ASSORTMENT_TEXT,
        reply_markup=assortment_kb(),
    )

    await callback.answer()


# =========================================================
# FAQ
# =========================================================

FAQ = [
    (
        "Как оформить заказ?",
        "1️⃣ Нажмите «Сделать заказ» и отправьте ссылку, фото, "
        "цену в ¥, количество и размер.\n"
        "2️⃣ Проверьте корзину, лишнее можно удалить.\n"
        "3️⃣ Нажмите «Отправить менеджеру» — заявка уйдёт "
        "менеджеру, дальше он на связи.",
    ),
    (
        "Как считается стоимость?",
        f"Цена в юанях × курс ({EXCHANGE_RATE:.2f} ₽) "
        f"+ комиссия сервиса {MARKUP_PERCENT:g}%. "
        "Быстро прикинуть можно в «Калькуляторе».",
    ),
    (
        "Сколько стоит доставка?",
        f"{PRICE_PER_KG:.0f} ₽ за 1 кг по фактическому весу. "
        "Вес определяется при взвешивании на складе, поэтому "
        "доставка не входит в сумму заказа сразу и "
        "оплачивается после взвешивания.",
    ),
    (
        "Как работают бонусы?",
        f"Вы приглашаете друга по своей ссылке — за каждый кг его "
        f"заказа вам начисляется {REFERRAL_BONUS_PER_KG:.0f} ₽. "
        "Баланс учитывается менеджером как скидка на ваш "
        "следующий заказ.",
    ),
    (
        "Как отследить заказ?",
        "Раздел «Мои заказы» показывает все заявки и их статусы: "
        + ", ".join(STATUS_OPTIONS)
        + ".",
    ),
    (
        "Как связаться с менеджером?",
        f"Напишите {MANAGER_USERNAME} — ответит по любому "
        "вопросу по заказу.",
    ),
]


def _faq_list_kb() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=question,
                callback_data=f"faq:{i}",
            )
        ]
        for i, (question, _) in enumerate(FAQ)
    ]

    rows.append(
        [
            InlineKeyboardButton(
                text="🏠 В меню",
                callback_data="menu:home",
            )
        ]
    )

    return InlineKeyboardMarkup(inline_keyboard=rows)


@router.callback_query(F.data == "menu:faq")
async def menu_faq(
    callback: CallbackQuery,
    state: FSMContext,
):
    await state.clear()

    await send_header(callback.message, "faq")

    await callback.message.answer(
        "❓ <b>[ FAQ ]</b>\n\nВыберите вопрос:",
        reply_markup=_faq_list_kb(),
    )

    await callback.answer()


@router.callback_query(F.data == "menu:faqlist")
async def menu_faq_list(
    callback: CallbackQuery,
    state: FSMContext,
):
    # «К вопросам» — без повторной картинки
    await state.clear()

    await callback.message.answer(
        "❓ <b>[ FAQ ]</b>\n\nВыберите вопрос:",
        reply_markup=_faq_list_kb(),
    )

    await callback.answer()


@router.callback_query(F.data.startswith("faq:"))
async def faq_answer(callback: CallbackQuery):

    try:
        question, answer = FAQ[int(callback.data.split(":")[1])]
    except (ValueError, IndexError):
        await callback.answer()
        return

    await callback.message.answer(
        f"❓ <b>{question}</b>\n\n{answer}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="◀️ К вопросам",
                        callback_data="menu:faqlist",
                    ),
                    InlineKeyboardButton(
                        text="🏠 В меню",
                        callback_data="menu:home",
                    ),
                ]
            ]
        ),
    )

    await callback.answer()
