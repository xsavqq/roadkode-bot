from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message

import database as db
from keyboards import main_menu, closed_links_kb

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await db.ensure_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name or "",
    )

    await message.answer(
        "👋 <b>Добро пожаловать в ROADKODE LOGISTICS!</b>\n\n"
        "Я помогу оформить заказ из Китая: пришли ссылку или "
        "фото товара — рассчитаю стоимость и передам заявку "
        "менеджеру.\n\n"
        "Выберите действие ниже 👇",
        reply_markup=main_menu,
    )


@router.message(F.text == "ℹ️ О боте")
async def about_bot(message: Message):
    await message.answer(
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
        "не пропустите",
        reply_markup=main_menu,
    )


@router.message(F.text == "📦 Как оформить заказ")
async def order_instruction(message: Message):
    await message.answer(
        "📦 <b>Как оформить заказ:</b>\n\n"
        "1️⃣ Нажмите «Добавить товар» и заполните все шаги.\n\n"
        "2️⃣ Проверьте корзину и при необходимости удалите лишнее.\n\n"
        "3️⃣ Нажмите «Оформить заказ» и следуйте инструкции.\n\n"
        "❌ Отменить заполнение можно кнопкой «Отмена».",
        reply_markup=main_menu,
    )


@router.message(F.text == "🔒 Закрытый чат и канал")
async def closed_links(message: Message):
    await message.answer(
        "Доступ для клиентов сервиса:",
        reply_markup=closed_links_kb,
    )
