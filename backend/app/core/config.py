from pydantic_settings import BaseSettings
from pathlib import Path


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/studyai"

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
    CORS_ORIGINS: list[str] = ["http://localhost:4200"]

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
