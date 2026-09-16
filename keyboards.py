from aiogram.fsm.state import State, StatesGroup


# =========================================================
# ОФОРМЛЕНИЕ ЗАКАЗА
# =========================================================

class OrderStates(StatesGroup):

    # Ссылка на товар
    waiting_link = State()

    # Фото / скрин товара
    waiting_photo = State()

    # Цена в юанях
    waiting_price = State()

    # Количество
    waiting_qty = State()

    # Размер
    waiting_size = State()

    # Оставлено для совместимости со старой БД/логикой.
    # В новом оформлении клиент сюда НЕ попадает.
    waiting_weight = State()


# =========================================================
# ЛИЧНЫЙ КАБИНЕТ
# =========================================================

class CabinetStates(StatesGroup):

    waiting_name = State()

    waiting_phone = State()


# =========================================================
# РЕДАКТИРОВАНИЕ ТОВАРА
# =========================================================

class EditItemStates(StatesGroup):

    waiting_new_price = State()


# =========================================================
# МЕНЕДЖЕР
# =========================================================

class AdminStates(StatesGroup):

    # Менеджер вводит фактический вес заказа
    waiting_order_weight = State()
