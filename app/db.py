import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "questions.db"


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


def add_question(client_user_id, client_mention, fio, city, phone, question_text, public_message_id):
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO questions (client_user_id, client_mention, fio, city, phone, question_text, public_message_id) VALUES (?,?,?,?,?,?,?)",
            (client_user_id, client_mention, fio, city, phone, question_text, public_message_id),
        )
        return cur.lastrowid


def get_question(question_id):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM questions WHERE id=?", (question_id,)).fetchone()
        return dict(row) if row else None


def save_answer(question_id, answer_text):
    with get_conn() as conn:
        conn.execute("UPDATE questions SET answer_text=? WHERE id=?", (answer_text, question_id))


def mark_published(question_id):
    with get_conn() as conn:
        conn.execute("UPDATE questions SET published=1 WHERE id=?", (question_id,))
