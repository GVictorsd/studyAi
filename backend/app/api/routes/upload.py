from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.models import Textbook, Exam
from app.schemas.schemas import UploadResponse, ExamUploadResponse, TextbookOut
from app.agents.textbook_knowledge_agent import textbook_knowledge_agent
from app.services.storage_service import storage_service

router = APIRouter(prefix="/upload", tags=["Upload"])

textbook_router = APIRouter(prefix="/textbooks", tags=["Textbooks"])


@textbook_router.get("", response_model=list[TextbookOut])
async def list_textbooks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Textbook).order_by(Textbook.uploaded_at.desc()))
    return result.scalars().all()


@router.post("/textbook", response_model=UploadResponse)
async def upload_textbook(
    file: UploadFile = File(...),
    title: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ("application/pdf", "text/plain"):
        raise HTTPException(400, "Only PDF or plain text files are accepted.")

    file_path = await storage_service.save_textbook(file)

    textbook = Textbook(
        title=title,
        file_path=str(file_path),
    )
    db.add(textbook)
    await db.commit()
    await db.refresh(textbook)

    text = storage_service.read_text_from_path(str(file_path))
    if text.strip():
        collection_name = textbook_knowledge_agent.index(textbook.id, text)
        textbook.chroma_collection_id = collection_name
        textbook.is_indexed = True
        await db.commit()

    return UploadResponse(
        id=textbook.id,
        filename=file.filename or "textbook",
        message="Textbook uploaded and indexed successfully.",
    )


@router.post("/exam", response_model=ExamUploadResponse)
async def upload_exam(
    student_id: str = Form(...),
    textbook_id: str = Form(None),
    file: UploadFile = File(None),
    exam_text: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    if not file and not exam_text:
        raise HTTPException(400, "Provide either an exam file or exam_text.")

    file_path = None
    if file:
        file_path = await storage_service.save_exam_paper(file)

    exam = Exam(
        student_id=student_id,
        textbook_id=textbook_id,
        exam_paper_path=str(file_path) if file_path else None,
        exam_text=exam_text,
    )
    db.add(exam)
    await db.commit()
    await db.refresh(exam)

    return ExamUploadResponse(
        exam_id=exam.id,
        message="Exam paper uploaded successfully.",
    )


@router.post("/answers", response_model=ExamUploadResponse)
async def upload_answers(
    exam_id: str = Form(...),
    file: UploadFile = File(None),
    answer_text: str = Form(None),
    db: AsyncSession = Depends(get_db),
):
    if not file and not answer_text:
        raise HTTPException(400, "Provide either an answer file or answer_text.")

    exam = await db.get(Exam, exam_id)
    if not exam:
        raise HTTPException(404, f"Exam {exam_id} not found.")

    if file:
        file_path = await storage_service.save_answer_sheet(file)
        exam.answer_sheet_path = str(file_path)

    if answer_text:
        exam.answer_text = answer_text

    await db.commit()

    return ExamUploadResponse(
        exam_id=exam.id,
        message="Answer sheet uploaded successfully.",
    )
