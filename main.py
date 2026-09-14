import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyParameters

from app import db
from app.config import settings
from app.keyboards import get_cancel_keyboard, get_main_menu_keyboard
from app.states import LawyerStates, MyCaseStates

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()

BOT_USERNAME = "feedback_FCB_bot"
LINK_CONSULT = "https://фцб.рф/яготов"
LINK_REFER = "https://фцб.рф/зовисвоих"
LINK_REVIEW_BOT = "https://t.me/uk_review_bot"

PIN_TEXT = (
    "👋 Добро пожаловать в чат клиентов ФЦБ!\n\n"
    "Здесь юристы публично отвечают на вопросы, а завершённые клиенты делятся опытом.\n\n"
    "📌 Как это работает: нажмите нужную кнопку ниже — бот напишет вам в личные сообщения и проведёт по шагам. Личные данные остаются конфиденциальными: в общий чат попадает только короткое уведомление.\n\n"
    "Выбирайте раздел:"
)


def mention(user) -> str:
    return f"@{user.username}" if user.username else user.full_name


def open_bot_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="📩 Открыть бота", url=f"https://t.me/{BOT_USERNAME}?start=menu")]]
    )


async def send_private(user_id: int, text: str, reply_markup=None) -> bool:
    try:
        await bot.send_message(user_id, text, reply_markup=reply_markup)
        return True
    except TelegramForbiddenError:
        return False


async def post_to_chat(text: str):
    try:
        return await bot.send_message(settings.CHAT_ID, text)
    except Exception as e:
        logger.error("Не удалось отправить пост в чат: %s", e)
        return None


@dp.message(CommandStart())
async def cmd_start(message: Message):
    logger.info("/start от %s (%s)", message.from_user.id, message.from_user.username)
    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\n"
        "Я помощник чата клиентов ФЦБ.\n"
        "Выберите нужный раздел в меню ниже:",
        reply_markup=get_main_menu_keyboard(),
    )


@dp.message(Command("pin_menu"))
async def cmd_pin_menu(message: Message):
    if message.from_user.id not in settings.LAWYER_IDS:
        await message.answer("⛔ Команда доступна только сотрудникам ФЦБ.")
        return
    msg = await bot.send_message(settings.CHAT_ID, PIN_TEXT, reply_markup=get_main_menu_keyboard())
    try:
        await bot.pin_chat_message(chat_id=settings.CHAT_ID, message_id=msg.message_id, disable_notification=True)
        await message.answer("✅ Меню опубликовано и закреплено в чате.")
    except Exception as e:
        logger.error("Не удалось закрепить: %s", e)
        await message.answer("⚠️ Меню опубликовано, но закрепить не удалось. Проверь права админа у бота в чате.")


@dp.callback_query(F.data == "consultation")
async def cb_consultation(callback: CallbackQuery):
    await callback.answer()
    await post_to_chat(f"{mention(callback.from_user)} хочет получить консультацию юриста по банкротству и перешел по ссылке фцб.рф/яготов")
    ok = await send_private(callback.from_user.id, "Переходите по ссылке, чтобы оставить заявку на консультацию:\n" + LINK_CONSULT)
    if not ok:
        await callback.message.answer(f"{mention(callback.from_user)}, не могу написать вам в личку. Нажмите кнопку ниже и отправьте боту /start:", reply_markup=open_bot_keyboard())


@dp.callback_query(F.data == "refer_friend")
async def cb_refer_friend(callback: CallbackQuery):
    await callback.answer()
    await post_to_chat(f"{mention(callback.from_user)} хочет помочь близкому и перешел по ссылке фцб.рф/зовисвоих")
    ok = await send_private(callback.from_user.id, "Переходите по ссылке, чтобы помочь близкому и заработать:\n" + LINK_REFER)
    if not ok:
        await callback.message.answer(f"{mention(callback.from_user)}, не могу написать вам в личку. Нажмите кнопку ниже и отправьте боту /start:", reply_markup=open_bot_keyboard())


@dp.callback_query(F.data == "video_review")
async def cb_video_review(callback: CallbackQuery):
    await callback.answer()
    await post_to_chat(f"{mention(callback.from_user)} участвует в конкурсе видеотзывов @uk_review_bot")
    ok = await send_private(callback.from_user.id, "Спасибо, что делитесь опытом! 🎥\nПереходите в бот конкурса и отправьте видеотзыв:\n" + LINK_REVIEW_BOT)
    if not ok:
        await callback.message.answer(f"{mention(callback.from_user)}, не могу написать вам в личку. Нажмите кнопку ниже и отправьте боту /start:", reply_markup=open_bot_keyboard())


@dp.callback_query(F.data.in_({"faq", "agent_payout"}))
async def cb_stub(callback: CallbackQuery):
    await callback.answer("Раздел подключается следующим шагом 🔧", show_alert=True)


@dp.callback_query(F.data == "my_case")
async def cb_my_case(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.set_state(MyCaseStates.waiting_fio)
    ok = await send_private(
        callback.from_user.id,
        "📁 Передам ваш вопрос юристу. Отвечайте по шагам.\n\n"
        "Шаг 1/4. Напишите ваши ФИО:",
        reply_markup=get_cancel_keyboard(),
    )
    if not ok:
        await state.clear()
        await callback.message.answer(f"{mention(callback.from_user)}, не могу написать вам в личку. Нажмите кнопку ниже, отправьте /start и выберите «Хочу узнать о моем деле» в меню:", reply_markup=open_bot_keyboard())


@dp.message(MyCaseStates.waiting_fio)
async def fsm_fio(message: Message, state: FSMContext):
    await state.update_data(fio=message.text)
    await state.set_state(MyCaseStates.waiting_city)
    await message.answer("Шаг 2/4. Напишите ваш город:", reply_markup=get_cancel_keyboard())


@dp.message(MyCaseStates.waiting_city)
async def fsm_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(MyCaseStates.waiting_phone)
    await message.answer("Шаг 3/4. Напишите ваш контактный телефон:", reply_markup=get_cancel_keyboard())


@dp.message(MyCaseStates.waiting_phone)
async def fsm_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(MyCaseStates.waiting_question)
    await message.answer("Шаг 4/4. Напишите ваш вопрос в свободной форме:", reply_markup=get_cancel_keyboard())


@dp.message(MyCaseStates.waiting_question)
async def fsm_question(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    public_msg = await post_to_chat(f"{mention(message.from_user)} задал вопрос юристу")
    public_id = public_msg.message_id if public_msg else 0
    qid = db.add_question(
        message.from_user.id,
        mention(message.from_user),
        data.get("fio", ""),
        data.get("city", ""),
        data.get("phone", ""),
        message.text,
        public_id,
    )

    await message.answer("✅ Вопрос передан юристу. Ответ придёт публично в общий чат — я вас уведомлю.")

    card = (
        f"🔔 Вопрос #{qid}\n"
        f"👤 Клиент: {data.get('fio')} (г. {data.get('city')})\n"
        f"📞 {data.get('phone')}\n"
        f"🆔 Telegram: {mention(message.from_user)} (id {message.from_user.id})\n"
        f"❓ {message.text}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✍️ Ответить на вопрос", callback_data=f"lawyer_reply:{qid}")]])
    for lid in settings.LAWYER_IDS:
        try:
            await bot.send_message(lid, card, reply_markup=kb)
        except Exception as e:
            logger.error("Не удалось отправить карточку юристу %s: %s", lid, e)


@dp.callback_query(F.data == "cancel_fsm")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.answer("❌ Отменено. Меню остаётся доступным.")


@dp.callback_query(F.data.startswith("lawyer_reply:"))
async def cb_lawyer_reply(callback: CallbackQuery, state: FSMContext):
    qid = int(callback.data.split(":")[1])
    if callback.from_user.id not in settings.LAWYER_IDS:
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await callback.answer()
    await state.set_state(LawyerStates.waiting_answer)
    await state.update_data(question_id=qid)
    await callback.message.answer("Напишите ответ следующим сообщением:")


@dp.message(LawyerStates.waiting_answer)
async def fsm_lawyer_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    qid = data.get("question_id")
    await state.clear()
    db.save_answer(qid, message.text)
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Опубликовать в общем чате", callback_data=f"publish:{qid}")],
            [InlineKeyboardButton(text="✏️ Переписать", callback_data=f"rewrite:{qid}")],
        ]
    )
    await message.answer(f"Ответ сохранён:\n\n{message.text}\n\nЧто дальше?", reply_markup=kb)


@dp.callback_query(F.data.startswith("rewrite:"))
async def cb_rewrite(callback: CallbackQuery, state: FSMContext):
    qid = int(callback.data.split(":")[1])
    if callback.from_user.id not in settings.LAWYER_IDS:
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await callback.answer()
    await state.set_state(LawyerStates.waiting_answer)
    await state.update_data(question_id=qid)
    await callback.message.answer("Напишите новую версию ответа:")


@dp.callback_query(F.data.startswith("publish:"))
async def cb_publish(callback: CallbackQuery):
    qid = int(callback.data.split(":")[1])
    if callback.from_user.id not in settings.LAWYER_IDS:
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    q = db.get_question(qid)
    if not q or not q["answer_text"]:
        await callback.answer("Ответ не найден", show_alert=True)
        return
    text = f"Ответ юриста ФЦБ:\n\n{q['answer_text']}"
    try:
        if q["public_message_id"]:
            await bot.send_message(settings.CHAT_ID, text, reply_parameters=ReplyParameters(message_id=q["public_message_id"]))
        else:
            await bot.send_message(settings.CHAT_ID, text)
    except Exception as e:
        logger.error("Не удалось опубликовать: %s", e)
        await callback.answer("Не удалось опубликовать в чат (возможно, пост удалён)", show_alert=True)
        return
    db.mark_published(qid)
    await callback.message.edit_text(f"✅ Вопрос #{qid} опубликован в общем чате.")
    try:
        await bot.send_message(q["client_user_id"], "🎉 Юрист ответил на ваш вопрос в общем чате! Загляните посмотреть.")
    except Exception:
        pass
    await callback.answer("Опубликовано!")


async def main():
    db.init_db()
    logger.info("Запуск бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

