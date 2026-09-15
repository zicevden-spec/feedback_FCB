import asyncio
import logging
from urllib.parse import quote

from aiogram import Bot, Dispatcher, F
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.strategy import FSMStrategy
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
    ReplyKeyboardRemove,
    ReplyParameters,
)

from app import audit, db, roles, webapi, worktime
from app.admin import router as admin_router
from app.config import settings
from app.faq import router as faq_router
from app.keyboards import get_cancel_keyboard, get_main_menu_keyboard, get_phone_keyboard, get_url_keyboard
from app.payout import router as payout_router
from app.states import LawyerStates, MyCaseStates

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher(fsm_strategy=FSMStrategy.GLOBAL_USER)
dp.include_router(faq_router)
dp.include_router(payout_router)
dp.include_router(admin_router)

PRIVATE = F.chat.type == "private"

BLOCKED_OUTSIDE_HOURS = {"consultation", "my_case", "refer_friend", "agent_payout"}

BOT_USERNAME = "feedback_FCB_bot"
LINK_CONSULT = "https://фцб.рф/яготов"
LINK_REFER = "https://фцб.рф/зовисвоих"
LINK_REVIEW_BOT = "https://t.me/uk_review_bot"

ANSWER_TITLES = {"q": "Ответ юриста ФЦБ:", "p": "Ответ сотрудника ФЦБ:"}

PIN_TEXT = (
    "👋 Добро пожаловать в чат клиентов ФЦБ!\n\n"
    "Здесь юристы публично отвечают на вопросы, а завершённые клиенты делятся опытом.\n\n"
    "📌 Как это работает: нажмите нужную кнопку ниже — бот напишет вам в личные сообщения и проведёт по шагам. Личные данные остаются конфиденциальными: в общий чат попадает только короткое уведомление.\n\n"
    "Выбирайте раздел:"
)


@dp.callback_query.outer_middleware()
async def worktime_guard(handler, event, data):
    audit.log_callback(event)
    if event.data in BLOCKED_OUTSIDE_HOURS and not worktime.is_working_now():
        await event.answer()
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="📚 Открыть FAQ", callback_data="faq")]]
        )
        ok = await send_private(event.from_user.id, worktime.closed_text(), reply_markup=kb)
        if not ok:
            await event.message.answer(worktime.closed_text(), reply_markup=kb)
        return None
    return await handler(event, data)


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
    payload = message.text.split(" ", 1)[1].strip() if message.text and " " in message.text else ""
    if payload.startswith("ref_") and payload[4:].isdigit():
        ref_id = int(payload[4:])
        if ref_id != message.from_user.id:
            db.add_referral(ref_id, message.from_user.id, mention(message.from_user))
    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\n"
        "Я помощник чата клиентов ФЦБ.\n"
        "Выберите нужный раздел в меню ниже:",
        reply_markup=get_main_menu_keyboard(roles.can_manage(message.from_user.id)),
    )


@dp.message(Command("pin_menu"))
async def cmd_pin_menu(message: Message):
    if not roles.is_staff(message.from_user.id):
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
    # [OFF] await post_to_chat(f"{mention(callback.from_user)} хочет получить консультацию юриста по банкротству и перешел по ссылке фцб.рф/яготов")
    ok = await send_private(callback.from_user.id, "Нажмите кнопку ниже — она откроет лендинг «Я готов»:", reply_markup=get_url_keyboard("🚀 Перейти на лендинг «Я готов»", LINK_CONSULT))
    if not ok:
        await callback.message.answer(f"{mention(callback.from_user)}, не могу написать вам в личку. Нажмите кнопку ниже и отправьте боту /start:", reply_markup=open_bot_keyboard())


@dp.callback_query(F.data == "refer_friend")
async def cb_refer_friend(callback: CallbackQuery):
    await callback.answer()
    # [OFF] await post_to_chat(f"{mention(callback.from_user)} хочет помочь близкому и перешел по ссылке фцб.рф/зовисвоих")
    uid = callback.from_user.id
    ref_link = f"{LINK_REFER}?ref={uid}"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Поделиться ссылкой", url=f"https://t.me/share/url?url={ref_link}&text={quote('Помоги близкому списать долги вместе с ФЦБ!')}")],
        [InlineKeyboardButton(text="🚀 Перейти на лендинг «Зови своих»", url=LINK_REFER)],
        [InlineKeyboardButton(text="📊 Мои рефералы", callback_data="my_refs")],
    ])
    ok = await send_private(
        callback.from_user.id,
        "🤝 Реферальная программа ФЦБ\n\n"
        "Помогите близкому списать долги — и получите вознаграждение.\n\n"
        f"🔗 Ваша личная ссылка:\n{ref_link}\n\n"
        "Когда близкий перейдёт по ней и зарегистрируется — он запишется на ваш счёт.",
        reply_markup=kb,
    )
    if not ok:
        await callback.message.answer(f"{mention(callback.from_user)}, не могу написать вам в личку. Нажмите кнопку ниже и отправьте боту /start:", reply_markup=open_bot_keyboard())


@dp.callback_query(F.data == "video_review")
async def cb_video_review(callback: CallbackQuery):
    await callback.answer()
    if worktime.is_working_now():
        await post_to_chat(f"{mention(callback.from_user)} участвует в конкурсе видеотзывов @uk_review_bot")
    ok = await send_private(callback.from_user.id, "Нажмите кнопку ниже — она откроет бот конкурса видеотзывов:", reply_markup=get_url_keyboard("🎥 Перейти в бот видеотзывов", LINK_REVIEW_BOT))
    if not ok:
        await callback.message.answer(f"{mention(callback.from_user)}, не могу написать вам в личку. Нажмите кнопку ниже и отправьте боту /start:", reply_markup=open_bot_keyboard())


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


@dp.message(MyCaseStates.waiting_fio, PRIVATE)
async def fsm_fio(message: Message, state: FSMContext):
    await state.update_data(fio=message.text)
    await state.set_state(MyCaseStates.waiting_city)
    await message.answer("Шаг 2/4. Напишите ваш город:", reply_markup=get_cancel_keyboard())


@dp.message(MyCaseStates.waiting_city, PRIVATE)
async def fsm_city(message: Message, state: FSMContext):
    await state.update_data(city=message.text)
    await state.set_state(MyCaseStates.waiting_phone)
    await message.answer(
        "Шаг 3/4. Нажмите кнопку «📱 Поделиться номером» ниже — и телефон отправится автоматически.\n"
        "Либо введите телефон вручную текстом:",
        reply_markup=get_phone_keyboard(),
    )


@dp.message(MyCaseStates.waiting_phone, F.contact, PRIVATE)
async def fsm_phone_contact(message: Message, state: FSMContext):
    await state.update_data(phone=message.contact.phone_number)
    await state.set_state(MyCaseStates.waiting_question)
    await message.answer(
        "✅ Контакт получен!\n\nШаг 4/4. Напишите ваш вопрос в свободной форме:",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(MyCaseStates.waiting_phone, PRIVATE)
async def fsm_phone_text(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(MyCaseStates.waiting_question)
    await message.answer(
        "✅ Телефон принят!\n\nШаг 4/4. Напишите ваш вопрос в свободной форме:",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.message(MyCaseStates.waiting_question, PRIVATE)
async def fsm_question(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    public_text = f"{mention(message.from_user)} задал вопрос юристу:\n\n«{message.text}»"
    public_msg = await post_to_chat(public_text)
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

    await message.answer(
        "✅ Вопрос передан юристу.\n"
        "Ответ придёт публично в общий чат — я вас уведомлю.",
    )

    card = (
        f"🔔 Вопрос #{qid}\n"
        f"👤 Клиент: {data.get('fio')} (г. {data.get('city')})\n"
        f"📞 {data.get('phone')}\n"
        f"🆔 Telegram: {mention(message.from_user)} (id {message.from_user.id})\n"
        f"❓ {message.text}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="✍️ Ответить на вопрос", callback_data=f"lawyer_reply:q:{qid}")]])
    for lid in roles.card_recipients():
        try:
            await bot.send_message(lid, card, reply_markup=kb)
        except Exception as e:
            logger.error("Не удалось отправить карточку сотруднику %s: %s", lid, e)


@dp.callback_query(F.data == "cancel_fsm")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.answer("❌ Отменено. Меню остаётся доступным.")


@dp.callback_query(F.data.startswith("lawyer_reply:"))
async def cb_lawyer_reply(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    kind, rid = parts[1], int(parts[2])
    if not roles.is_staff(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await callback.answer()
    await state.set_state(LawyerStates.waiting_answer)
    await state.update_data(question_kind=kind, question_id=rid)
    await callback.message.answer("Напишите ответ следующим сообщением:")


@dp.message(LawyerStates.waiting_answer, PRIVATE)
async def fsm_lawyer_answer(message: Message, state: FSMContext):
    data = await state.get_data()
    kind = data.get("question_kind", "q")
    rid = data.get("question_id")
    await state.clear()
    db.save_answer(kind, rid, message.text, message.from_user.id, mention(message.from_user))
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📢 Опубликовать в общем чате", callback_data=f"publish:{kind}:{rid}")],
            [InlineKeyboardButton(text="✏️ Переписать", callback_data=f"rewrite:{kind}:{rid}")],
        ]
    )
    await message.answer(f"Ответ сохранён:\n\n{message.text}\n\nЧто дальше?", reply_markup=kb)


@dp.callback_query(F.data.startswith("rewrite:"))
async def cb_rewrite(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    kind, rid = parts[1], int(parts[2])
    if not roles.is_staff(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await callback.answer()
    await state.set_state(LawyerStates.waiting_answer)
    await state.update_data(question_kind=kind, question_id=rid)
    await callback.message.answer("Напишите новую версию ответа:")


@dp.callback_query(F.data.startswith("publish:"))
async def cb_publish(callback: CallbackQuery):
    parts = callback.data.split(":")
    kind, rid = parts[1], int(parts[2])
    if not roles.is_staff(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    rec = db.get_record(kind, rid)
    if not rec or not rec["answer_text"]:
        await callback.answer("Ответ не найден", show_alert=True)
        return
    text = f"{ANSWER_TITLES.get(kind, 'Ответ ФЦБ:')}\n\n{rec['answer_text']}"
    try:
        if rec["public_message_id"]:
            await bot.send_message(settings.CHAT_ID, text, reply_parameters=ReplyParameters(message_id=rec["public_message_id"]))
        else:
            await bot.send_message(settings.CHAT_ID, text)
    except Exception as e:
        logger.error("Не удалось опубликовать: %s", e)
        await callback.answer("Не удалось опубликовать в чат (возможно, пост удалён)", show_alert=True)
        return
    db.mark_published(kind, rid)
    await callback.message.edit_text(f"✅ Обращение #{rid} опубликовано в общем чате.")
    try:
        await bot.send_message(rec["client_user_id"], "🎉 Сотрудник ФЦБ ответил на ваш вопрос в общем чате! Загляните посмотреть.")
    except Exception:
        pass
    await callback.answer("Опубликовано!")


@dp.callback_query(F.data == "my_refs")
async def cb_my_refs(callback: CallbackQuery):
    await callback.answer()
    refs = db.list_refs(callback.from_user.id)
    if not refs:
        await send_private(callback.from_user.id, "Пока никто не перешёл по вашей ссылке.\nПоделитесь личной ссылкой — и рефералы появятся здесь!")
        return
    lines = [f"• {r['referred_username'] or r['referred_id']} — {r['created_at'][:10]}" for r in refs[:10]]
    await send_private(callback.from_user.id, f"📊 Ваши рефералы: {len(refs)}\n\nПоследние:\n" + "\n".join(lines))


async def main():
    db.init_db()
    roles.seed_super_admins()
    await webapi.start(bot)
    logger.info("Запуск бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())


