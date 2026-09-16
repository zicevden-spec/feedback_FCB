from aiogram import F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardRemove

from app import db, roles
from app.config import settings
from app.keyboards import get_cancel_keyboard, get_phone_keyboard
from app.states import AgentPayoutStates

router = Router()

PRIVATE = F.chat.type == "private"


def mention(user) -> str:
    return f"@{user.username}" if user.username else user.full_name


def open_bot_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="📩 Открыть бота", url="https://t.me/feedback_FCB_bot?start=menu")]]
    )


async def send_private(bot, user_id: int, text: str, reply_markup=None) -> bool:
    try:
        await bot.send_message(user_id, text, reply_markup=reply_markup)
        return True
    except TelegramForbiddenError:
        return False


async def post_to_chat(bot, text: str):
    try:
        return await bot.send_message(settings.CHAT_ID, text)
    except Exception:
        return None


@router.callback_query(F.data == "agent_payout")
async def cb_agent_payout(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(AgentPayoutStates.waiting_agent_fio)
    ok = await send_private(
        callback.bot,
        callback.from_user.id,
        "💰 Уточню статус вашей Агентской выплаты. Отвечайте по шагам.\n\n"
        "Шаг 1/5. Напишите ваши ФИО (как агента):",
        reply_markup=get_cancel_keyboard(),
    )
    if not ok:
        await state.clear()
        await callback.message.answer(f"{mention(callback.from_user)}, чтобы продолжать получать информацию, перейдите в бота:", reply_markup=open_bot_keyboard())


@router.message(AgentPayoutStates.waiting_agent_fio, PRIVATE)
async def fsm_agent_fio(message: Message, state: FSMContext):
    await state.update_data(agent_fio=message.text)
    await state.set_state(AgentPayoutStates.waiting_agent_phone)
    await message.answer(
        "Шаг 2/5. Нажмите кнопку «📱 Поделиться номером» ниже — или введите ваш телефон вручную:",
        reply_markup=get_phone_keyboard(),
    )


@router.message(AgentPayoutStates.waiting_agent_phone, F.contact, PRIVATE)
async def fsm_agent_phone_contact(message: Message, state: FSMContext):
    await state.update_data(agent_phone=message.contact.phone_number)
    await state.set_state(AgentPayoutStates.waiting_client_fio)
    await message.answer("✅ Контакт получен!", reply_markup=ReplyKeyboardRemove())
    await message.answer("Шаг 3/5. Напишите ФИО клиента, по которому вы агент:", reply_markup=get_cancel_keyboard())


@router.message(AgentPayoutStates.waiting_agent_phone, PRIVATE)
async def fsm_agent_phone_text(message: Message, state: FSMContext):
    await state.update_data(agent_phone=message.text)
    await state.set_state(AgentPayoutStates.waiting_client_fio)
    await message.answer("✅ Телефон принят!", reply_markup=ReplyKeyboardRemove())
    await message.answer("Шаг 3/5. Напишите ФИО клиента, по которому вы агент:", reply_markup=get_cancel_keyboard())


@router.message(AgentPayoutStates.waiting_client_fio, PRIVATE)
async def fsm_client_fio(message: Message, state: FSMContext):
    await state.update_data(client_fio=message.text)
    await state.set_state(AgentPayoutStates.waiting_client_phone)
    await message.answer("Шаг 4/5. Напишите телефон клиента:", reply_markup=get_cancel_keyboard())


@router.message(AgentPayoutStates.waiting_client_phone, PRIVATE)
async def fsm_client_phone(message: Message, state: FSMContext):
    await state.update_data(client_phone=message.text)
    await state.set_state(AgentPayoutStates.waiting_question)
    await message.answer("Шаг 5/5. Напишите ваш вопрос по выплате в свободной форме:", reply_markup=get_cancel_keyboard())


@router.message(AgentPayoutStates.waiting_question, PRIVATE)
async def fsm_agent_question(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    # Публичный пост БЕЗ персональных данных
    # [OFF] public_msg = await post_to_chat(message.bot, f"{mention(message.from_user)} задал вопрос по Агентской выплате")
    # [OFF] public_id = public_msg.message_id if public_msg else 0
    public_id = 0  # заглушка, пока пост отключён

    pid = db.add_payout(
        message.from_user.id,
        mention(message.from_user),
        data.get("agent_fio", ""),
        data.get("agent_phone", ""),
        data.get("client_fio", ""),
        data.get("client_phone", ""),
        message.text,
        public_id,
    )

    await message.answer(
        "✅ Вопрос по Агентской выплате передан сотруднику.\n"
        "Ответ придёт публично в общий чат — я вас уведомлю.",
    )

    card = (
        f"💰 Запрос по выплате #{pid}\n"
        f"👤 Агент: {data.get('agent_fio')}\n"
        f"📞 Телефон агента: {data.get('agent_phone')}\n"
        f"👥 Клиент: {data.get('client_fio')}\n"
        f"📞 Телефон клиента: {data.get('client_phone')}\n"
        f"🆔 Telegram: {mention(message.from_user)} (id {message.from_user.id})\n"
        f"❓ {message.text}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✍️ Ответить", callback_data=f"lawyer_reply:p:{pid}")]])
    for lid in roles.card_recipients():
        try:
            await message.bot.send_message(lid, card, reply_markup=kb)
        except Exception:
            pass



