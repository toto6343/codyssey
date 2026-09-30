import os

from dotenv import load_dotenv

load_dotenv()


def _split(value: str) -> list[str]:
    return [o.strip().rstrip("/") for o in value.split(",") if o.strip()]


class Settings:
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "")
    firebase_credentials: str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON", "")
    allowed_origins: list[str] = _split(
        os.getenv("ALLOWED_ORIGINS", "http://localhost:5500,http://127.0.0.1:5500,http://localhost:3000")
    )
    kobis_api_key: str = os.getenv("KOBIS_API_KEY", "")
    chat_max_tokens: int = int(os.getenv("CHAT_MAX_TOKENS", "500"))
    chat_max_history: int = int(os.getenv("CHAT_MAX_HISTORY", "10"))


settings = Settings()
