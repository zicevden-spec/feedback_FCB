from app import db

CALLBACK_TITLES = {
    "consultation": "Клик: консультация",
    "my_case": "Клик: мое дело (начало опроса)",
    "refer_friend": "Клик: помочь близкому",
    "video_review": "Клик: видеоотзыв",
    "faq": "Клик: открыть FAQ",
    "agent_payout": "Клик: агентская выплата (начало опроса)",
    "admin_panel": "Клик: админ панель",
    "admin_staff": "Админка: раздел сотрудники",
    "admin_stats": "Админка: статистика",
    "admin_export": "Админка: выгрузка Excel",
    "admin_list": "Админка: список сотрудников",
    "main_menu": "Навигация: главное меню",
    "faq_back": "Навигация: список FAQ",
    "cancel_fsm": "Отмена опроса",
}

PREFIX_TITLES = [
    ("faq_item:", "FAQ: открыт вопрос"),
    ("lawyer_reply:", "Сотрудник: начал писать ответ"),
    ("publish:", "Сотрудник: опубликовал ответ в чат"),
    ("rewrite:", "Сотрудник: переписывает ответ"),
    ("admin_add:", "Админка: добавление сотрудника"),
    ("admin_remove:", "Админка: удаление сотрудника"),
]


def title_for(data: str) -> str:
    if data in CALLBACK_TITLES:
        return CALLBACK_TITLES[data]
    for prefix, title in PREFIX_TITLES:
        if data.startswith(prefix):
            return title
    return f"Клик: {data}"


def log_callback(callback) -> None:
    """Пишет в журнал любое нажатие любой кнопки."""
    user = callback.from_user
    db.log_event(
        user.id,
        f"@{user.username}" if user.username else user.full_name,
        title_for(callback.data or ""),
        f"чат: {callback.message.chat.type}",
    )
