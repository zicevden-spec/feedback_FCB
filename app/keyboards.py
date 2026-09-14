from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_menu_keyboard(is_manager: bool = False) -> InlineKeyboardMarkup:
    """Главное меню из 6 кнопок по ТЗ. Админам добавляется кнопка админ-панели."""
    builder = InlineKeyboardBuilder()

    builder.row(InlineKeyboardButton(text="💬 Хочу получить консультацию и списать долги", callback_data="consultation"))
    builder.row(InlineKeyboardButton(text="📁 Хочу узнать о моем деле", callback_data="my_case"))
    builder.row(InlineKeyboardButton(text="🤝 Хочу помочь близкому и заработать", callback_data="refer_friend"))
    builder.row(InlineKeyboardButton(text="❓ Хочу узнать о банкротстве больше (FAQ)", callback_data="faq"))
    builder.row(InlineKeyboardButton(text="🎥 Хочу оставить видеоотзыв", callback_data="video_review"))
    builder.row(InlineKeyboardButton(text="💰 Хочу узнать, где моя Агентская выплата", callback_data="agent_payout"))

    if is_manager:
        builder.row(InlineKeyboardButton(text="⚙️ Админ панель", callback_data="admin_panel"))

    return builder.as_markup()


def get_cancel_keyboard() -> InlineKeyboardMarkup:
    """Инлайн-кнопка отмены для FSM-диалогов"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_fsm"))
    return builder.as_markup()


def get_phone_keyboard() -> ReplyKeyboardMarkup:
    """Reply-клавиатура с кнопкой «Поделиться номером»"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться номером", request_contact=True)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
