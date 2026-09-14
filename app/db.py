import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "questions.db"

# kind -> таблица: q = вопросы клиентов, p = агентские выплаты
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
