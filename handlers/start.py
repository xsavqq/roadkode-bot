from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.filters.command import CommandObject
from aiogram.types import Message

import database as db
from config import CLOSED_CHAT_URL, CLOSED_CHANNEL_URL, MANAGER_USERNAME
from keyboards import main_menu

router = Router()


WELCOME_TEXT = (
    "🚚 <b>Добро пожаловать в ROADKODE!</b>\n\n"
    "Заказывайте товары из Китая проще — без лишних расчётов и переписок.\n\n"
    "🔗 Отправьте ссылку на товар\n"
    "📷 Пришлите фото или скрин товара\n"
    "🤖 Бот поможет оценить примерный вес\n"
    "💴 Рассчитает стоимость товара\n"
    "📦 Оформит заказ и поможет отслеживать его статус\n"
    "⚠️ Стоимость доставки рассчитывается после фактического взвешивания товара.\n\n"
    "👇 Нажмите <b>«🛒 Новый заказ»</b>, чтобы начать."
)


HOW_TO_ORDER_TEXT = (
    "📦 <b>Как оформить заказ:</b>\n\n"
    "1️⃣ Нажмите «🛒 Новый заказ» и заполните все шаги.\n\n"
    "2️⃣ Проверьте корзину и при необходимости удалите лишнее.\n\n"
    "3️⃣ Нажмите «📩 Отправить менеджеру» и следуйте инструкции.\n\n"
    "❌ Отменить заполнение можно кнопкой «❌ Отмена»."
)


ABOUT_TEXT = (
    "🤖 <b>Что умеет этот бот?</b>\n\n"
    "Это бот для выкупа и доставки товаров из Китая. "
    "Присылаешь ссылку или фото товара — бот сам считает "
    "стоимость (цена + доставка по Китаю + комиссия), "
    "а менеджер оформляет заказ.\n\n"
    "🛍 Можно добавить сразу несколько товаров в корзину "
    "и отправить одной заявкой\n"
    "👤 После первого заказа откроется личный кабинет — "
    "там видно статус всех заявок\n"
    "🎟 Периодически действуют промокоды на скидку — "
    "не пропустите\n\n"
    f"📢 Основной канал: {CLOSED_CHANNEL_URL}\n"
    f"💬 Чат наших клиентов и бесплатная таблица "
    f"поставщиков: {CLOSED_CHAT_URL}\n"
    f"🆘 Поддержка / менеджер: {MANAGER_USERNAME}"
)


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    referred_by = None
    if command.args and command.args.startswith("ref_"):
        try:
            referred_by = int(command.args[4:])
        except ValueError:
            referred_by = None

    await db.ensure_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name or "",
        referred_by=referred_by,
    )

    await message.answer(
        WELCOME_TEXT,
        reply_markup=main_menu,
    )


@router.message(F.text == "📦 Как оформить заказ")
async def how_to_order(message: Message):
    await message.answer(
        HOW_TO_ORDER_TEXT,
        reply_markup=main_menu,
    )


@router.message(F.text == "ℹ️ О боте")
async def about_bot(message: Message):
    await message.answer(
        ABOUT_TEXT,
        reply_markup=main_menu,
    )
