import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "questions.db"

TABLE_BY_KIND = {"q": "questions", "p": "payouts"}


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
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
                created_at TEXT DEFAULT (datetime('now', 'localtime'))
            )
            """
        )


# ---------- Вопросы и выплаты ----------

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


def save_answer(kind, record_id, answer_text):
    table = TABLE_BY_KIND[kind]
    with get_conn() as conn:
        conn.execute(f"UPDATE {table} SET answer_text=? WHERE id=?", (answer_text, record_id))


def mark_published(kind, record_id):
    table = TABLE_BY_KIND[kind]
    with get_conn() as conn:
        conn.execute(f"UPDATE {table} SET published=1 WHERE id=?", (record_id,))


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


def set_role(user_id, role, added_by=0):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO users (user_id, role, added_by) VALUES (?,?,?) "
            "ON CONFLICT(user_id) DO UPDATE SET role=excluded.role, added_by=excluded.added_by",
            (user_id, role, added_by),
        )


def remove_staff(user_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM users WHERE user_id=?", (user_id,))


def list_staff():
    with get_conn() as conn:
        rows = conn.execute("SELECT user_id, role, added_by FROM users ORDER BY role, user_id").fetchall()
        return [dict(r) for r in rows]


def staff_ids(roles):
    with get_conn() as conn:
        placeholders = ",".join("?" for _ in roles)
        rows = conn.execute(f"SELECT user_id FROM users WHERE role IN ({placeholders})", tuple(roles)).fetchall()
        return [r["user_id"] for r in rows]
