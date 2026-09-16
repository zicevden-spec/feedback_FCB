from aiogram import F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app import roles
from app.keyboards import get_main_menu_keyboard

router = Router()

FAQ_ITEMS = [
    {
        "id": "what",
        "label": "❓ Что такое банкротство физлиц?",
        "answer": (
            "Это законная процедура (ФЗ № 127 «О несостоятельности (банкротстве)»), "
            "при которой человек официально признаётся неспособным платить по долгам.\n\n"
            "После её завершения человек полностью освобождается от большинства долгов: "
            "кредитов, микрозаймов, кредитных карт, долгов по ЖКХ и налогам."
        ),
    },
    {
        "id": "who",
        "label": "❓ Кому подходит банкротство?",
        "answer": (
            "Банкротство подходит любому человеку, который не справляется с долгами.\n\n"
            "Обязаны подавать при долге от 300 000 ₽ и просрочке от 3 месяцев. "
            "Но можно и при меньшем долге, если платить объективно нечем: "
            "нет стабильного дохода, платежи превышают доход, выплаты уже остановлены."
        ),
    },
    {
        "id": "property",
        "label": "❓ Что будет с моим имуществом?",
        "answer": (
            "Единственное жильё (квартира, дом) защищено законом и НЕ изымается — "
            "кроме случаев, когда оно в ипотеке.\n\n"
            "Обычные бытовые вещи и техника остаются. Реализовать могут только предметы "
            "роскоши (второй автомобиль, драгоценности), и то под контролем суда — на практике это редкость."
        ),
    },
    {
        "id": "not_discharged",
        "label": "❓ Какие долги НЕ списываются?",
        "answer": (
            "Не списываются: алименты, возмещение вреда жизни и здоровью, моральный вред, "
            "а также долги, возникшие ПОСЛЕ подачи на банкротство.\n\n"
            "Всё остальное (кредиты, микрозаймы, кредитные карты, ЖКХ, налоги, штрафы) списывается полностью."
        ),
    },
    {
        "id": "duration",
        "label": "❓ Сколько длится процедура?",
        "answer": (
            "В среднем 6–10 месяцев от подачи заявления до решения суда.\n\n"
            "Подготовка и сбор документов занимают 2–4 недели. "
            "Точный срок зависит от загруженности суда и сложности вашей ситуации."
        ),
    },
    {
        "id": "consequences",
        "label": "❓ Какие последствия банкротства?",
        "answer": (
            "Во время процедуры: счета контролирует финуправляющий, возможен временный запрет на выезд за границу.\n\n"
            "После завершения: 5 лет нужно сообщать о банкротстве при взятии кредитов, "
            "3 года нельзя занимать должности руководителя юрлица, 5 лет нельзя банкротиться повторно.\n\n"
            "Других ограничений нет: можно работать, получать доход, путешествовать по России."
        ),
    },
]

FAQ_MENU_TEXT = (
    "📚 FAQ о банкротстве\n\n"
    "Выберите вопрос — отвечу подробно:"
)


def faq_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for item in FAQ_ITEMS:
        builder.row(InlineKeyboardButton(text=item["label"], callback_data=f"faq_item:{item['id']}"))
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def faq_item_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⬅️ К списку FAQ", callback_data="faq"))
    builder.row(InlineKeyboardButton(text="🏠 Главное меню", callback_data="main_menu"))
    return builder.as_markup()


def open_bot_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="📩 Открыть бота", url="https://t.me/feedback_FCB_bot?start=menu")]]
    )


async def send_private(bot, user_id: int, text: str, markup=None) -> bool:
    try:
        await bot.send_message(user_id, text, reply_markup=markup)
        return True
    except TelegramForbiddenError:
        return False


@router.callback_query(F.data == "faq")
async def cb_faq_menu(callback: CallbackQuery):
    await callback.answer()
    ok = await send_private(callback.bot, callback.from_user.id, FAQ_MENU_TEXT, faq_menu_keyboard())
    if not ok:
        await callback.message.answer("Чтобы продолжать получать информацию, перейдите в бота:", reply_markup=open_bot_keyboard())


@router.callback_query(F.data.startswith("faq_item:"))
async def cb_faq_item(callback: CallbackQuery):
    item_id = callback.data.split(":")[1]
    item = next((i for i in FAQ_ITEMS if i["id"] == item_id), None)
    if not item:
        await callback.answer("Вопрос не найден", show_alert=True)
        return
    await callback.answer()
    ok = await send_private(callback.bot, callback.from_user.id, item["answer"], faq_item_keyboard())
    if not ok:
        await callback.message.answer("Чтобы продолжать получать информацию, перейдите в бота:", reply_markup=open_bot_keyboard())


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery):
    await callback.answer()
    ok = await send_private(callback.bot, callback.from_user.id, "Выберите нужный раздел:", get_main_menu_keyboard(roles.can_manage(callback.from_user.id)))
    if not ok:
        await callback.message.answer("Чтобы продолжать получать информацию, перейдите в бота:", reply_markup=open_bot_keyboard())


