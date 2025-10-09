from aiogram.fsm.state import State, StatesGroup

class ViewStates(StatesGroup):
    WAITING_FOR_SECTION = State()
    WAITING_FOR_ANSWER = State()
    IN_MAIN_MENU = State()