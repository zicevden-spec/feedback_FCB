from aiogram.fsm.state import State, StatesGroup


class MyCaseStates(StatesGroup):
    """Состояния для кнопки «Хочу узнать о моем деле»"""
    waiting_fio = State()
    waiting_city = State()
    waiting_phone = State()
    waiting_question = State()


class AgentPayoutStates(StatesGroup):
    """Состояния для кнопки «Хочу узнать, где моя Агентская выплата»"""
    waiting_agent_fio = State()
    waiting_agent_phone = State()
    waiting_client_fio = State()
    waiting_client_phone = State()
    waiting_question = State()


class LawyerStates(StatesGroup):
    """Состояния юриста: написание ответа"""
    waiting_answer = State()
