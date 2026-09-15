from datetime import datetime
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font

from app import db, roles


def _autowidth(ws):
    for col in ws.columns:
        width = max((len(str(c.value)) for c in col if c.value is not None), default=10)
        ws.column_dimensions[col[0].column_letter].width = min(width + 2, 60)
    for c in ws[1]:
        c.font = Font(bold=True)


def _status_of(rec):
    return rec["status"] or "Не обработан"


def build_report_xlsx() -> bytes:
    wb = Workbook()

    # ---------- Статистика ----------
    ws = wb.active
    ws.title = "Статистика"
    s = db.stats()
    q_wait = s["q_total"] - s["q_published"] - s["q_in_progress"]
    p_wait = s["p_total"] - s["p_published"] - s["p_in_progress"]
    for row in [
        ["Отчёт чат-бота ФЦБ", ""],
        ["Сформирован", datetime.now().strftime("%d.%m.%Y %H:%M")],
        ["", ""],
        ["Вопросы юристу", "Кол-во"],
        ["Всего", s["q_total"]],
        ["Отвечено в чате", s["q_published"]],
        ["Ответ написан, не опубликован", s["q_in_progress"]],
        ["Без ответа", q_wait],
        ["", ""],
        ["Агентские выплаты", "Кол-во"],
        ["Всего", s["p_total"]],
        ["Отвечено в чате", s["p_published"]],
        ["Ответ написан, не опубликован", s["p_in_progress"]],
        ["Без ответа", p_wait],
    ]:
        ws.append(row)
    ws["A1"].font = Font(bold=True, size=14)
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 20

    # ---------- Журнал обращений (колонки по ТЗ) ----------
    ws = wb.create_sheet("Журнал обращений")
    ws.append(["Дата и время", "Тип", "User ID", "Username", "Детали", "Вопрос", "Статус ответа", "Ответственный (ответил)", "Комментарий"])
    rows = []
    with db.get_conn() as conn:
        qs = conn.execute("SELECT * FROM questions").fetchall()
        ps = conn.execute("SELECT * FROM payouts").fetchall()
    for r in qs:
        rows.append((r["created_at"], r["id"], [
            r["created_at"], "Вопрос юристу", r["client_user_id"], r["client_mention"],
            f"ФИО: {r['fio']}; город: {r['city']}; телефон: {r['phone']}",
            r["question_text"], _status_of(r), r["answer_by_username"] or "", r["comment"] or "",
        ]))
    for r in ps:
        rows.append((r["created_at"], r["id"], [
            r["created_at"], "Агентская выплата", r["client_user_id"], r["client_mention"],
            f"Агент: {r['agent_fio']}, тел: {r['agent_phone']}; клиент: {r['client_fio']}, тел: {r['client_phone']}",
            r["question_text"], _status_of(r), r["answer_by_username"] or "", r["comment"] or "",
        ]))
    for _, _, row in sorted(rows, key=lambda x: (x[0], x[1])):
        ws.append(row)
    _autowidth(ws)

    # ---------- Журнал действий ----------
    ws = wb.create_sheet("Журнал действий")
    ws.append(["Дата и время", "User ID", "Username", "Действие", "Детали"])
    for e in reversed(db.list_events()):
        ws.append([e["created_at"], e["user_id"], e["username"], e["action"], e["details"]])
    _autowidth(ws)

    # ---------- Сотрудники ----------
    ws = wb.create_sheet("Сотрудники")
    ws.append(["Telegram ID", "Username", "Роль"])
    for srow in db.list_staff():
        ws.append([srow["user_id"], srow["username"] or "", roles.ROLE_TITLES.get(srow["role"], srow["role"])])
    _autowidth(ws)

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()

