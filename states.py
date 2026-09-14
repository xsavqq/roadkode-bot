from aiogram.fsm.state import State, StatesGroup


class OrderStates(StatesGroup):
    waiting_link = State()      # ссылка на товар / фото / "-"
    waiting_price = State()     # цена в юанях
    waiting_qty = State()       # количество
    waiting_size = State()      # размер или "-"


class CabinetStates(StatesGroup):
    waiting_name = State()
    waiting_phone = State()


class EditItemStates(StatesGroup):
    waiting_new_price = State()
