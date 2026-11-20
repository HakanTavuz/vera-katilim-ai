import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _flag(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes", "on")


class Settings:
    def __init__(self) -> None:
        self.SECURE_MODE = _flag("SECURE_MODE")
        self.SECRET_KEY = os.getenv("SECRET_KEY", "")
        self.DATA_ENCRYPTION_KEY = os.getenv("DATA_ENCRYPTION_KEY", "")
        self.DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
        self.DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "securebank.db"))

        if not self.SECRET_KEY:
            raise RuntimeError("SECRET_KEY is missing. Copy .env.example to .env and fill it in.")


# Mutable on purpose: tests flip SECURE_MODE at runtime, so always read it at call time.
settings = Settings()
