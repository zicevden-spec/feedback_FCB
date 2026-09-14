import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    GOOGLE_CREDENTIALS_JSON: str = os.getenv("GOOGLE_CREDENTIALS_JSON")
    GOOGLE_SHEET_ID: str = os.getenv("GOOGLE_SHEET_ID")
    CHAT_ID: int = int(os.getenv("CHAT_ID", 0))
    LAWYER_IDS: list = [int(x) for x in os.getenv("LAWYER_IDS", "").split(",") if x.strip()]


settings = Settings()
