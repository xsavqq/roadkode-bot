import logging
import os

from aiogram.types import (
    FSInputFile,
    Message,
    ReplyKeyboardRemove,
)

from config import (
    BANNER_PATH,
    EXCHANGE_RATE,
    PRICE_PER_KG,
    REFERRAL_BONUS_PER_KG,
)

from keyboards import main_inline_kb


# =========================================================
# ТЕКСТ ГЛАВНОГО ЭКРАНА (подпись под баннером)
# =========================================================

def home_text() -> str:
    return (
        "<b>[ ROADKODE ]</b>  заказы из Китая\n\n"

        "🛒 Выкуп товара и доставка без лишних переписок\n"
        f"💴 Курс юаня: <b>{EXCHANGE_RATE:.2f} ₽</b>\n"
        f"🚚 Доставка: <b>{PRICE_PER_KG:.0f} ₽/кг</b> "
        "после взвешивания\n"
        f"🎁 Друзьям — скидка, вам — "
        f"<b>{REFERRAL_BONUS_PER_KG:.0f} ₽</b> за каждый их кг\n\n"

        "👇 Выберите действие"
    )


# file_id баннера после первой отправки — чтобы не грузить файл каждый раз
_banner_file_id: str | None = None


async def send_home(message: Message) -> None:
    """
    Главный экран: баннер + текст + inline-кнопки одним сообщением.
    Если баннера нет или Telegram его не принял — просто текст.
    """

    global _banner_file_id

    text = home_text()
    kb = main_inline_kb()

    if _banner_file_id or os.path.exists(BANNER_PATH):

        try:
            photo = (
                _banner_file_id
                or FSInputFile(BANNER_PATH)
            )

            sent = await message.answer_photo(
                photo,
                caption=text,
                reply_markup=kb,
            )

            _banner_file_id = sent.photo[-1].file_id

            return

        except Exception as exc:
            logging.warning(
                "Banner send failed: %r", exc
            )

    await message.answer(
        text,
        reply_markup=kb,
    )


async def drop_reply_kb(message: Message) -> None:
    """
    Убирает нижнюю reply-клавиатуру («❌ Отмена» и т.п.):
    шлёт служебное сообщение с ReplyKeyboardRemove и удаляет его.
    """

    try:
        tmp = await message.answer(
            "🔄",
            reply_markup=ReplyKeyboardRemove(),
        )
        await tmp.delete()
    except Exception:
        pass
