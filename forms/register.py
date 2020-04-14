from aiogram.dispatcher.filters.state import State, StatesGroup


class Register(StatesGroup):
    name = State()
    age = State()
    phone_number = State()
