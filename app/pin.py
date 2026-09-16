from app.keyboards import get_main_menu_keyboard

PIN_TEXT = (
    "👋 Добро пожаловать в чат клиентов ФЦБ!\n\n"
    "Здесь юристы публично отвечают на вопросы, а завершённые клиенты делятся опытом.\n\n"
    "📌 Как это работает: нажмите нужную кнопку ниже — бот напишет вам в личные сообщения и проведёт по шагам. Личные данные остаются конфиденциальными: в общий чат попадает только короткое уведомление.\n\n"
    "Выбирайте раздел:"
)


async def publish_pin_menu(bot, chat_id: int):
    """Публикует меню в чат и закрепляет. Возвращает (ok, error)."""
    try:
        msg = await bot.send_message(chat_id, PIN_TEXT, reply_markup=get_main_menu_keyboard())
    except Exception as e:
        return False, f"отправка: {e}"
    try:
        await bot.pin_chat_message(chat_id=chat_id, message_id=msg.message_id, disable_notification=True)
    except Exception as e:
        return True, f"закреп: {e}"
    return True, None
