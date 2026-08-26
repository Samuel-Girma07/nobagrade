from aiogram.fsm.state import State, StatesGroup

class CheckCreditStates(StatesGroup):
    waiting_for_api_key = State()
