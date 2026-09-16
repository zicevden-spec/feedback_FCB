from datetime import datetime

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app import db, export, roles
from app.config import settings
from app.keyboards import get_cancel_keyboard, get_main_menu_keyboard
from app.states import AdminStates

router = Router()

PRIVATE = F.chat.type == "private"


def _kb(rows):
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_menu_keyboard():
    return _kb([
        [InlineKeyboardButton(text="👥 Сотрудники", callback_data="admin_staff")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📥 Выгрузить отчёт (Excel)", callback_data="admin_export")],
        [InlineKeyboardButton(text="📌 Опубликовать меню в закреп", callback_data="admin_pin_menu")],
        [InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")],
    ])


def staff_menu_keyboard(user_id):
    rows = []
    if roles.is_superadmin(user_id):
        rows.append([InlineKeyboardButton(text="➕ Добавить админа", callback_data="admin_add:admin")])
    rows.append([InlineKeyboardButton(text="➕ Добавить юриста", callback_data="admin_add:lawyer")])
    rows.append([InlineKeyboardButton(text="📋 Список сотрудников", callback_data="admin_list")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")])
    return _kb(rows)


@router.callback_query(F.data == "admin_panel")
async def cb_admin_panel(callback: CallbackQuery):
    if not roles.can_manage(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await callback.answer()
    role_title = roles.ROLE_TITLES.get(roles.get_role(callback.from_user.id), "")
    await callback.message.edit_text(
        f"⚙️ Админ панель\n\nВаша роль: {role_title}\nВыберите раздел:",
        reply_markup=admin_menu_keyboard(),
    )


@router.callback_query(F.data == "admin_staff")
async def cb_admin_staff(callback: CallbackQuery):
    if not roles.can_manage(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text(
        "👥 Управление сотрудниками\n\nВыберите действие:",
        reply_markup=staff_menu_keyboard(callback.from_user.id),
    )


@router.callback_query(F.data.startswith("admin_add:"))
async def cb_admin_add(callback: CallbackQuery, state: FSMContext):
    target_role = callback.data.split(":")[1]
    if not roles.can_manage(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    if target_role == "admin" and not roles.is_superadmin(callback.from_user.id):
        await callback.answer("Добавлять админов может только супер-админ", show_alert=True)
        return
    await callback.answer()
    await state.set_state(AdminStates.waiting_target)
    await state.update_data(target_role=target_role)
    title = roles.ROLE_TITLES[target_role]
    await callback.message.answer(
        f"Пришлите Telegram ID (цифрами) или @username нового сотрудника (роль: {title}):",
        reply_markup=get_cancel_keyboard(),
    )


@router.message(AdminStates.waiting_target, PRIVATE)
async def fsm_admin_target(message: Message, state: FSMContext):
    data = await state.get_data()
    target_role = data.get("target_role")
    text = (message.text or "").strip()

    user_id = None
    if text.isdigit():
        user_id = int(text)
    elif text.startswith("@"):
        try:
            chat = await message.bot.get_chat(text)
            user_id = chat.id
        except Exception:
            user_id = None

    if not user_id:
        await message.answer("Не удалось распознать ID или username. Попробуйте ещё раз (цифры или @username):")
        return

    if roles.get_role(user_id) == roles.ROLE_SUPERADMIN:
        await state.clear()
        await message.answer("⛔ Этот пользователь уже супер-админ — его роль изменить нельзя.")
        return

    uname = text if text.startswith("@") else ""
    try:
        chat = await message.bot.get_chat(user_id)
        uname = chat.username or uname
    except Exception:
        pass
    db.set_role(user_id, target_role, message.from_user.id, uname)
    await state.clear()
    title = roles.ROLE_TITLES[target_role]
    await message.answer(f"✅ Готово: пользователю {user_id} назначена роль «{title}».")
    try:
        await message.bot.send_message(user_id, f"🎉 Вам назначена роль «{title}» в боте чата клиентов ФЦБ.")
    except Exception:
        pass


@router.callback_query(F.data == "admin_list")
async def cb_admin_list(callback: CallbackQuery):
    if not roles.can_manage(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await callback.answer()
    staff = db.list_staff()
    if not staff:
        await callback.message.edit_text(
            "📋 Список сотрудников пуст.",
            reply_markup=_kb([[InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_staff")]]),
        )
        return

    lines = []
    rows = []
    for s in staff:
        title = roles.ROLE_TITLES.get(s["role"], s["role"])
        lines.append(f"• {title} — id {s['user_id']}")

        can_remove = False
        if s["role"] == roles.ROLE_ADMIN:
            can_remove = roles.is_superadmin(callback.from_user.id)
        elif s["role"] == roles.ROLE_LAWYER:
            can_remove = roles.can_manage(callback.from_user.id)
        if s["user_id"] == callback.from_user.id:
            can_remove = False

        if can_remove:
            rows.append([InlineKeyboardButton(text=f"❌ Убрать {s['user_id']}", callback_data=f"admin_remove:{s['user_id']}")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_staff")])

    await callback.message.edit_text(
        "📋 Сотрудники:\n\n" + "\n".join(lines),
        reply_markup=_kb(rows),
    )


@router.callback_query(F.data.startswith("admin_remove:"))
async def cb_admin_remove(callback: CallbackQuery):
    uid = int(callback.data.split(":")[1])
    role = roles.get_role(uid)
    if not roles.can_manage(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    if role == roles.ROLE_SUPERADMIN:
        await callback.answer("Супер-админа убрать нельзя", show_alert=True)
        return
    if role == roles.ROLE_ADMIN and not roles.is_superadmin(callback.from_user.id):
        await callback.answer("Убирать админов может только супер-админ", show_alert=True)
        return
    if uid == callback.from_user.id:
        await callback.answer("Нельзя убрать самого себя", show_alert=True)
        return
    db.remove_staff(uid)
    await callback.answer(f"Убран: {uid}")
    await callback.message.answer(f"✅ Сотрудник {uid} убран из сотрудников.")


@router.callback_query(F.data == "admin_stats")
async def cb_admin_stats(callback: CallbackQuery):
    if not roles.can_manage(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await callback.answer()
    s = db.stats()
    q_wait = s["q_total"] - s["q_published"] - s["q_in_progress"]
    p_wait = s["p_total"] - s["p_published"] - s["p_in_progress"]
    text = (
        "📊 Статистика\n\n"
        "❓ Вопросы юристу:\n"
        f"   Всего: {s['q_total']}\n"
        f"   ✅ Отвечено в чате: {s['q_published']}\n"
        f"   ✍️ Ответ написан, не опубликован: {s['q_in_progress']}\n"
        f"   ⏳ Без ответа: {q_wait}\n\n"
        "💰 Агентские выплаты:\n"
        f"   Всего: {s['p_total']}\n"
        f"   ✅ Отвечено в чате: {s['p_published']}\n"
        f"   ✍️ Ответ написан, не опубликован: {s['p_in_progress']}\n"
        f"   ⏳ Без ответа: {p_wait}\n"
    )
    await callback.message.edit_text(
        text,
        reply_markup=_kb([
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_stats")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_panel")],
        ]),
    )



@router.callback_query(F.data == "admin_export")
async def cb_admin_export(callback: CallbackQuery):
    if not roles.can_manage(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await callback.answer("Формирую отчёт...")
    data = export.build_report_xlsx()
    fname = "FCB_report_" + datetime.now().strftime("%Y-%m-%d_%H%M") + ".xlsx"
    await callback.message.answer_document(
        BufferedInputFile(data, filename=fname),
        caption="📥 Отчёт ФЦБ: статистика, вопросы, выплаты, сотрудники",
    )




@router.callback_query(F.data == "admin_pin_menu")
async def cb_admin_pin_menu(callback: CallbackQuery):
    if not roles.can_manage(callback.from_user.id):
        await callback.answer("Доступ запрещён", show_alert=True)
        return
    await callback.answer("Публикую и закрепляю...")
    from app.config import settings as _settings
    from app.pin import publish_pin_menu
    ok, err = await publish_pin_menu(callback.bot, _settings.CHAT_ID)
    if ok and err is None:
        await callback.message.answer("✅ Меню опубликовано и закреплено в чате.")
    elif ok:
        await callback.message.answer("✅ Меню опубликовано, но закрепить не удалось: " + str(err))
    else:
        await callback.message.answer("⚠️ Не удалось опубликовать меню: " + str(err))