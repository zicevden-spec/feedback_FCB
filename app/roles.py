from app import db
from app.config import settings

ROLE_SUPERADMIN = "superadmin"
ROLE_ADMIN = "admin"
ROLE_LAWYER = "lawyer"
ROLE_USER = "user"

ROLE_TITLES = {
    ROLE_SUPERADMIN: "Супер-админ",
    ROLE_ADMIN: "Админ",
    ROLE_LAWYER: "Юрист",
}

STAFF_ROLES = {ROLE_SUPERADMIN, ROLE_ADMIN, ROLE_LAWYER}
MANAGE_ROLES = {ROLE_SUPERADMIN, ROLE_ADMIN}


def get_role(user_id: int) -> str:
    return db.get_role(user_id)


def is_staff(user_id: int) -> bool:
    return get_role(user_id) in STAFF_ROLES


def can_manage(user_id: int) -> bool:
    return get_role(user_id) in MANAGE_ROLES


def is_superadmin(user_id: int) -> bool:
    return get_role(user_id) == ROLE_SUPERADMIN


def card_recipients() -> list:
    """Кому приходят карточки вопросов и выплат: юристы + супер-админы."""
    return db.staff_ids([ROLE_LAWYER, ROLE_SUPERADMIN])


def seed_super_admins() -> None:
    """При старте бота создаёт супер-админов из .env."""
    for uid in settings.SUPER_ADMIN_IDS:
        db.set_role(uid, ROLE_SUPERADMIN, 0)
