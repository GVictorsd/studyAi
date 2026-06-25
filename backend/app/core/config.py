from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Database — defaults to embedded SQLite for local dev; set to a
    # postgresql+asyncpg:// URL in .env (or via Docker) for production.
    DATABASE_URL: str = "sqlite+aiosqlite:///./studyai.db"

    # Google AI
    GOOGLE_API_KEY: str = ""
    GOOGLE_GENAI_USE_VERTEXAI: bool = False

    # Storage
    STORAGE_BASE_PATH: str = "./storage"

    # ChromaDB
    CHROMA_PERSIST_DIR: str = "./chroma_db"

    # App
    APP_ENV: str = "development"
    SECRET_KEY: str = "change_me"
    # Comma-separated list of allowed origins, e.g. "http://localhost:4200,http://localhost:3000"
    CORS_ORIGINS: str = "http://localhost:4200,http://localhost:4202"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def textbooks_path(self) -> Path:
        return Path(self.STORAGE_BASE_PATH) / "textbooks"

    @property
    def exam_papers_path(self) -> Path:
        return Path(self.STORAGE_BASE_PATH) / "exam_papers"

    @property
    def uploads_path(self) -> Path:
        return Path(self.STORAGE_BASE_PATH) / "uploads"


settings = Settings()
