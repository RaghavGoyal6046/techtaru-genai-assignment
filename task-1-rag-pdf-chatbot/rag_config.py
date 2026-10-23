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


class RAGConfig:
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
    GEMINI_FALLBACK_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")

    _configured_provider: str = os.getenv("LLM_PROVIDER", "").lower()

    @classmethod
    def get_active_provider(cls) -> str:
        if cls._configured_provider in ["gemini", "mock"]:
            return cls._configured_provider
        if cls.GEMINI_API_KEY:
            return "gemini"
        return "mock"

    CHUNK_SIZE: int = int(os.getenv("RAG_CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("RAG_CHUNK_OVERLAP", "200"))
    TOP_K: int = int(os.getenv("RAG_TOP_K", "3"))
    RELEVANCE_DISTANCE_THRESHOLD: float = float(os.getenv("RAG_DISTANCE_THRESHOLD", "0.82"))

    MAX_FILE_SIZE_MB: int = 25
    MIN_EXTRACTABLE_CHARS: int = 30
    PERSIST_DIRECTORY: str = str(Path(__file__).resolve().parent / "chroma_db_store")
