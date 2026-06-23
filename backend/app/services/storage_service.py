import uuid
import aiofiles
from pathlib import Path
from fastapi import UploadFile
from app.core.config import settings


class StorageService:
    """Handles local filesystem storage for uploaded PDFs and text files."""

    def __init__(self):
        self._ensure_dirs()

    def _ensure_dirs(self):
        for path in [
            settings.textbooks_path,
            settings.exam_papers_path,
            settings.uploads_path,
        ]:
            Path(path).mkdir(parents=True, exist_ok=True)

    async def save_file(self, file: UploadFile, destination: Path) -> Path:
        destination.mkdir(parents=True, exist_ok=True)
        suffix = Path(file.filename).suffix if file.filename else ".bin"
        unique_name = f"{uuid.uuid4()}{suffix}"
        file_path = destination / unique_name

        async with aiofiles.open(file_path, "wb") as out:
            content = await file.read()
            await out.write(content)

        return file_path

    async def save_textbook(self, file: UploadFile) -> Path:
        return await self.save_file(file, settings.textbooks_path)

    async def save_exam_paper(self, file: UploadFile) -> Path:
        return await self.save_file(file, settings.exam_papers_path)

    async def save_answer_sheet(self, file: UploadFile) -> Path:
        return await self.save_file(file, settings.uploads_path)

    def read_text_from_path(self, file_path: str) -> str:
        """Extract text from a stored PDF or text file."""
        path = Path(file_path)
        if not path.exists():
            return ""
        if path.suffix.lower() == ".pdf":
            return self._extract_pdf_text(path)
        return path.read_text(encoding="utf-8", errors="ignore")

    def _extract_pdf_text(self, path: Path) -> str:
        try:
            import pdfplumber
            with pdfplumber.open(str(path)) as pdf:
                return "\n\n".join(
                    page.extract_text() or "" for page in pdf.pages
                )
        except Exception:
            return ""


storage_service = StorageService()
