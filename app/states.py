from aiogram.fsm.state import State, StatesGroup


class MyCaseStates(StatesGroup):
    waiting_fio = State()
    waiting_city = State()
    waiting_phone = State()
    waiting_question = State()


class AgentPayoutStates(StatesGroup):
    waiting_agent_fio = State()
    waiting_agent_phone = State()
    waiting_client_fio = State()
    waiting_client_phone = State()
    waiting_question = State()


class LawyerStates(StatesGroup):
    waiting_answer = State()


class AdminStates(StatesGroup):
    waiting_target = State()
