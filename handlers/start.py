from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message

import database as db
from keyboards import main_menu, closed_links_kb

router = Router()


# =========================================================
# /START
# =========================================================

@router.message(CommandStart())
async def cmd_start(message: Message):
    await db.ensure_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name or "",
    )

    await message.answer(
        "🚚 <b>Добро пожаловать в ROADKODE!</b>\n\n"
        "Заказывайте товары из Китая проще — без лишних "
        "расчётов и переписок.\n\n"
        "🔗 Отправьте ссылку на товар\n"
        "📷 Пришлите фото или скрин\n"
        "🤖 Бот поможет оценить примерный вес\n"
        "💰 Рассчитает стоимость товара\n"
        "📦 А менеджер уточнит доставку после фактического "
        "взвешивания\n\n"
        "<b>Готовы? 👇</b>",
        reply_markup=main_menu,
    )


# =========================================================
# КАК ОФОРМИТЬ ЗАКАЗ
# =========================================================

@router.message(F.text == "📦 Как оформить заказ")
async def order_instruction(message: Message):
    await message.answer(
        "📦 <b>Как оформить заказ:</b>\n\n"
        "1️⃣ Нажмите «Добавить товар» и заполните все шаги.\n\n"
        "2️⃣ Проверьте корзину и при необходимости "
        "удалите лишнее.\n\n"
        "3️⃣ Нажмите «Оформить заказ» и следуйте инструкции.\n\n"
        "❌ Отменить заполнение можно кнопкой «Отмена».",
        reply_markup=main_menu,
    )


# =========================================================
# ЗАКРЫТЫЙ ЧАТ И КАНАЛ
# =========================================================

@router.message(F.text == "🔒 Закрытый чат и канал")
async def closed_links(message: Message):
    await message.answer(
        "Доступ для клиентов сервиса:",
        reply_markup=closed_links_kb,
    )
