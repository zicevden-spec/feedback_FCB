import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "questions.db"

TABLE_BY_KIND = {"q": "questions", "p": "payouts"}

# Миграция: колонки, которых нет в старых базах
MIGRATIONS = {
    "questions": [
        ("status", "TEXT DEFAULT 'Не обработан'"),
        ("answer_by_id", "INTEGER"),
        ("answer_by_username", "TEXT"),
        ("comment", "TEXT DEFAULT ''"),
    ],
    "payouts": [
        ("status", "TEXT DEFAULT 'Не обработан'"),
        ("answer_by_id", "INTEGER"),
        ("answer_by_username", "TEXT"),
        ("comment", "TEXT DEFAULT ''"),
    ],
"users": [
        ("username", "TEXT DEFAULT ''"),
    ],
}


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _migrate(conn):
    for table, cols in MIGRATIONS.items():
        existing = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        for name, ddl in cols:
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}")


def init_db():
    create_referrals_table()
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_user_id INTEGER,
                client_mention TEXT,
                fio TEXT,
                city TEXT,
                phone TEXT,
                question_text TEXT,
                public_message_id INTEGER,
                answer_text TEXT,
                published INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Не обработан',
                answer_by_id INTEGER,
                answer_by_username TEXT,
                comment TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payouts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_user_id INTEGER,
                client_mention TEXT,
                agent_fio TEXT,
                agent_phone TEXT,
                client_fio TEXT,
                client_phone TEXT,
                question_text TEXT,
                public_message_id INTEGER,
                answer_text TEXT,
                published INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Не обработан',
                answer_by_id INTEGER,
                answer_by_username TEXT,
                comment TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                role TEXT NOT NULL DEFAULT 'user',
                added_by INTEGER DEFAULT 0,
                username TEXT DEFAULT '',
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT DEFAULT (datetime('now', 'localtime')),
                user_id INTEGER,
                username TEXT,
                action TEXT,
                details TEXT DEFAULT ''
            )
            """
        )
        _migrate(conn)


# ---------- Обращения ----------

def add_question(client_user_id, client_mention, fio, city, phone, question_text, public_message_id):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO questions (client_user_id, client_mention, fio, city, phone, question_text, public_message_id) VALUES (?,?,?,?,?,?,?)",
            (client_user_id, client_mention, fio, city, phone, question_text, public_message_id),
        )
        return cur.lastrowid


def add_payout(client_user_id, client_mention, agent_fio, agent_phone, client_fio, client_phone, question_text, public_message_id):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO payouts (client_user_id, client_mention, agent_fio, agent_phone, client_fio, client_phone, question_text, public_message_id) VALUES (?,?,?,?,?,?,?,?)",
            (client_user_id, client_mention, agent_fio, agent_phone, client_fio, client_phone, question_text, public_message_id),
        )
        return cur.lastrowid


def get_record(kind, record_id):
    table = TABLE_BY_KIND[kind]
    with get_conn() as conn:
        row = conn.execute(f"SELECT * FROM {table} WHERE id=?", (record_id,)).fetchone()
        return dict(row) if row else None


def save_answer(kind, record_id, answer_text, by_id=0, by_username=""):
    table = TABLE_BY_KIND[kind]
    with get_conn() as conn:
        conn.execute(
            f"UPDATE {table} SET answer_text=?, status='В работе', answer_by_id=?, answer_by_username=? WHERE id=?",
            (answer_text, by_id, by_username, record_id),
        )


def mark_published(kind, record_id):
    table = TABLE_BY_KIND[kind]
    with get_conn() as conn:
        conn.execute(f"UPDATE {table} SET published=1, status='Отвечено' WHERE id=?", (record_id,))


def stats():
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT
                (SELECT COUNT(*) FROM questions) AS q_total,
                (SELECT COUNT(*) FROM questions WHERE published = 1) AS q_published,
                (SELECT COUNT(*) FROM questions WHERE answer_text IS NOT NULL AND published = 0) AS q_in_progress,
                (SELECT COUNT(*) FROM payouts) AS p_total,
                (SELECT COUNT(*) FROM payouts WHERE published = 1) AS p_published,
                (SELECT COUNT(*) FROM payouts WHERE answer_text IS NOT NULL AND published = 0) AS p_in_progress
            """
        ).fetchone()
        return dict(row)


# ---------- Роли ----------

def get_role(user_id):
    with get_conn() as conn:
        row = conn.execute("SELECT role FROM users WHERE user_id=?", (user_id,)).fetchone()
        return row["role"] if row else "user"


def set_role(user_id, role, added_by=0, username=""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO users (user_id, role, added_by, username) VALUES (?,?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET role=excluded.role, added_by=excluded.added_by, username=excluded.username",
            (user_id, role, added_by, username),
        )


def remove_staff(user_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM users WHERE user_id=?", (user_id,))


def list_staff():
    with get_conn() as conn:
        rows = conn.execute("SELECT user_id, role, added_by, username FROM users ORDER BY role, user_id").fetchall()
        return [dict(r) for r in rows]


def staff_ids(roles):
    with get_conn() as conn:
        placeholders = ",".join("?" for _ in roles)
        rows = conn.execute(f"SELECT user_id FROM users WHERE role IN ({placeholders})", tuple(roles)).fetchall()
        return [r["user_id"] for r in rows]


# ---------- Журнал действий ----------

def log_event(user_id, username, action, details=""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO events (user_id, username, action, details) VALUES (?,?,?,?)",
            (user_id, username, action, details),
        )


def list_events(limit=2000):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]



def register_lead(ref_id, phone, name=""):
    """Вебхук с лендинга: регистрация по реф-ссылке. Возвращает (referrer_id, created)."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM referrals WHERE referrer_id=? AND referred_phone=?",
            (ref_id, phone),
        ).fetchone()
        if row:
            if not row["registered_at"]:
                conn.execute(
                    "UPDATE referrals SET registered_at=datetime('now','localtime') WHERE id=?",
                    (row["id"],),
                )
            return row["referrer_id"], False
        conn.execute(
            "INSERT INTO referrals (referrer_id, referred_id, referred_username, referred_phone, registered_at) VALUES (?,?,?,?,datetime('now','localtime'))",
            (ref_id, 0, name, phone),
        )
        return ref_id, True



def create_referrals_table():
    """Создаёт таблицу referrals, если её нет."""
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                referred_username TEXT,
                referred_phone TEXT DEFAULT '',
                registered_at TEXT,
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
        """)

