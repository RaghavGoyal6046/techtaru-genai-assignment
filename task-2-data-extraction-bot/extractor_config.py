import os
from pathlib import Path
from dotenv import load_dotenv

local_env = Path(__file__).resolve().parent / ".env"
parent_env = Path(__file__).resolve().parent.parent / ".env"

if local_env.exists():
    load_dotenv(dotenv_path=local_env)
elif parent_env.exists():
    load_dotenv(dotenv_path=parent_env)
else:
    load_dotenv()


class ExtractorConfig:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    GEMINI_FALLBACK_MODEL: str = "gemini-3.5-flash-lite"

    _configured_provider: str = os.getenv("LLM_PROVIDER", "").lower()

    @classmethod
    def get_active_provider(cls) -> str:
        if cls._configured_provider in ["gemini", "mock"]:
            return cls._configured_provider
        if cls.GEMINI_API_KEY:
            return "gemini"
        return "mock"

    MAX_INPUT_CHARACTERS: int = 50000
    REQUEST_TIMEOUT_SECONDS: int = 30
