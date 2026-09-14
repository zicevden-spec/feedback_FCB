import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message

from app.config import settings
from app.keyboards import get_main_menu_keyboard

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

bot = Bot(token=settings.BOT_TOKEN)
dp = Dispatcher()

# Ссылки из ТЗ
LINK_CONSULT = "https://фцб.рф/яготов"
LINK_REFER = "https://фцб.рф/зовисвоих"
LINK_REVIEW_BOT = "https://t.me/uk_review_bot"


def mention(user) -> str:
    """@username или имя, если username скрыт."""
    return f"@{user.username}" if user.username else user.full_name


async def post_to_chat(text: str):
    """Публичный пост в чат клиентов. Ошибка не роняет бота."""
    try:
        await bot.send_message(settings.CHAT_ID, text)
    except Exception as e:
        logger.error("Не удалось отправить пост в чат: %s", e)


@dp.message(CommandStart())
async def cmd_start(message: Message):
    logger.info("/start от %s (%s)", message.from_user.id, message.from_user.username)
    await message.answer(
        f"Привет, {message.from_user.full_name}! 👋\n"
        "Я помощник чата клиентов ФЦБ.\n"
        "Выберите нужный раздел в меню ниже:",
        reply_markup=get_main_menu_keyboard(),
    )


@dp.callback_query(F.data == "consultation")
async def cb_consultation(callback: CallbackQuery):
    await callback.answer()
    await post_to_chat(f"{mention(callback.from_user)} хочет получить консультацию юриста по банкротству и перешел по ссылке фцб.рф/яготов")
    await callback.message.answer("Переходите по ссылке, чтобы оставить заявку на консультацию:\n" + LINK_CONSULT)


@dp.callback_query(F.data == "refer_friend")
async def cb_refer_friend(callback: CallbackQuery):
    await callback.answer()
    await post_to_chat(f"{mention(callback.from_user)} хочет помочь близкому и перешел по ссылке фцб.рф/зовисвоих")
    await callback.message.answer("Переходите по ссылке, чтобы помочь близкому и заработать:\n" + LINK_REFER)


@dp.callback_query(F.data == "video_review")
async def cb_video_review(callback: CallbackQuery):
    await callback.answer()
    await post_to_chat(f"{mention(callback.from_user)} участвует в конкурсе видеотзывов @uk_review_bot")
    await callback.message.answer("Спасибо, что делитесь опытом! 🎥\nПереходите в бот конкурса и отправьте видеотзыв:\n" + LINK_REVIEW_BOT)


@dp.callback_query(F.data.in_({"my_case", "faq", "agent_payout"}))
async def cb_stub(callback: CallbackQuery):
    await callback.answer()
    await callback.message.answer("Этот раздел подключим следующим шагом 🔧\nПока доступны: консультация, помощь близкому и видеоотзыв.")


async def main():
    logger.info("Запуск бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
