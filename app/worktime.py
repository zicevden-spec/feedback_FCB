from datetime import datetime, timedelta, timezone

from app.config import settings

try:
    from zoneinfo import ZoneInfo

    TZ = ZoneInfo("Europe/Moscow")
except Exception:
    TZ = timezone(timedelta(hours=3))

WEEKDAY_HOURS = (8, 20)   # будни
WEEKEND_HOURS = (10, 14)  # выходные


def is_working_now(now=None) -> bool:
    """Рабочее ли сейчас время (Москва). WORKTIME_MODE из .env может переопределить."""
    mode = (settings.WORKTIME_MODE or "").strip().lower()
    if mode == "open":
        return True
    if mode == "closed":
        return False
    now = now or datetime.now(TZ)
    start, end = WEEKDAY_HOURS if now.weekday() < 5 else WEEKEND_HOURS
    return start <= now.hour < end


def closed_text() -> str:
    return (
        "😴 Сейчас мы отдыхаем.\n\n"
        "🕒 Часы работы чата:\n"
        "• Будни: 8:00–20:00\n"
        "• Выходные: 10:00–14:00\n\n"
        "Ваш вопрос не потеряется: возвращайтесь в рабочее время.\n"
        "А прямо сейчас доступен FAQ — нажмите кнопку ниже:"
    )
