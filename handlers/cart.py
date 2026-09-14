from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

import database as db
from config import MANAGER_CHAT_ID, calc_cost
from states import EditItemStates
from keyboards import cart_footer_kb, cart_item_kb, admin_status_kb, main_menu

router = Router()


def _item_text(item) -> str:
    lines = [f"Товар: {item['link'] or '📎 фото / без ссылки'}"]
    lines.append(f"Цена: {item['price_yuan']:.0f} ¥  ×  {item['quantity']} шт.")
    lines.append(f"Размер: {item['size'] or 'не указан'}")
    lines.append(f"Стоимость: {item['cost_rub']:.0f} ₽")
    return "\n".join(lines)


@router.callback_query(F.data == "view_cart")
async def view_cart(callback: CallbackQuery):
    await show_cart(callback)


@router.message(F.text == "🛒 Посмотреть корзину")
async def view_cart_msg(message):
    items = await db.get_cart(message.from_user.id)
    if not items:
        await message.answer("Корзина пуста.", reply_markup=main_menu)
        return
    for item in items:
        if item["photo_id"]:
            await message.answer_photo(item["photo_id"], caption=_item_text(item),
                                        reply_markup=cart_item_kb(item["id"]))
        else:
            await message.answer(_item_text(item), reply_markup=cart_item_kb(item["id"]))
    total = await db.get_cart_total(message.from_user.id)
    await message.answer(f"Общая сумма: {total:.0f} ₽", reply_markup=cart_footer_kb())


async def show_cart(callback: CallbackQuery):
    user_id = callback.from_user.id
    items = await db.get_cart(user_id)
    if not items:
        await callback.message.answer("Корзина пуста.", reply_markup=main_menu)
        await callback.answer()
        return
    for item in items:
        if item["photo_id"]:
            await callback.message.answer_photo(item["photo_id"], caption=_item_text(item),
                                                  reply_markup=cart_item_kb(item["id"]))
        else:
            await callback.message.answer(_item_text(item), reply_markup=cart_item_kb(item["id"]))
    total = await db.get_cart_total(user_id)
    await callback.message.answer(f"Общая сумма: {total:.0f} ₽", reply_markup=cart_footer_kb())
    await callback.answer()


@router.callback_query(F.data.startswith("del_item:"))
async def delete_item(callback: CallbackQuery):
    item_id = int(callback.data.split(":")[1])
    await db.delete_cart_item(item_id, callback.from_user.id)
    total = await db.get_cart_total(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(f"🗑 Товар удалён.\nОбщая сумма: {total:.0f} ₽")
    await callback.answer("Удалено")


@router.callback_query(F.data.startswith("edit_item:"))
async def edit_item_start(callback: CallbackQuery, state: FSMContext):
    item_id = int(callback.data.split(":")[1])
    item = await db.get_cart_item(item_id, callback.from_user.id)
    if not item:
        await callback.answer("Товар не найден", show_alert=True)
        return
    await state.set_state(EditItemStates.waiting_new_price)
    await state.update_data(item_id=item_id)
    await callback.message.answer(
        f"Текущая цена: {item['price_yuan']:.0f} ¥, количество: {item['quantity']} шт.\n"
        f"Введите новую цену в юанях, только число."
    )
    await callback.answer()


@router.message(EditItemStates.waiting_new_price, F.text)
async def edit_item_price(message: Message, state: FSMContext):
    raw = message.text.strip().replace(",", ".")
    try:
        price = float(raw)
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ Нужно отправить число, например: 47 или 47.5")
        return

    data = await state.get_data()
    item = await db.get_cart_item(data["item_id"], message.from_user.id)
    if not item:
        await message.answer("Товар не найден.", reply_markup=main_menu)
        await state.clear()
        return

    new_cost = calc_cost(price, item["quantity"])
    await db.delete_cart_item(item["id"], message.from_user.id)
    await db.add_cart_item(
        user_id=message.from_user.id,
        link=item["link"],
        photo_id=item["photo_id"],
        price_yuan=price,
        quantity=item["quantity"],
        size=item["size"],
        cost_rub=new_cost,
    )
    total = await db.get_cart_total(message.from_user.id)
    await state.clear()
    await message.answer(
        f"✅ Цена обновлена.\nНовая стоимость товара: {new_cost:.0f} ₽\nОбщая сумма: {total:.0f} ₽",
        reply_markup=main_menu,
    )


@router.callback_query(F.data == "clear_cart")
async def clear_cart_cb(callback: CallbackQuery):
    await db.clear_cart(callback.from_user.id)
    await callback.message.answer("🗑 Корзина очищена.", reply_markup=main_menu)
    await callback.answer()


@router.callback_query(F.data == "send_to_manager")
async def send_to_manager(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    items = await db.get_cart(user_id)
    if not items:
        await callback.answer("Корзина пуста", show_alert=True)
        return

    order_id = await db.create_order_from_cart(user_id)
    order = await db.get_order(order_id)
    order_items = await db.get_order_items(order_id)

    user = callback.from_user
    header = (
        f"📦 Новая заявка №{order_id}\n"
        f"От: {user.full_name} (@{user.username or '—'}, id {user.id})\n\n"
    )
    body = "\n\n".join(_item_text(i) for i in order_items)
    footer = f"\n\nИтого: {order['total_rub']:.0f} ₽\nСтатус: {order['status']}"

    if MANAGER_CHAT_ID:
        await bot.send_message(
            MANAGER_CHAT_ID,
            header + body + footer,
            reply_markup=admin_status_kb(order_id),
        )

    await callback.message.answer(
        f"✅ Заявка №{order_id} отправлена менеджеру!\nИтого: {order['total_rub']:.0f} ₽",
        reply_markup=main_menu,
    )
    await callback.answer()
