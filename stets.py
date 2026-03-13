from aiogram.fsm.state import StatesGroup, State


class SendImg(StatesGroup):
    image = State()
    about = State()
    confirm = State()