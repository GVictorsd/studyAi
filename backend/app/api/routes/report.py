from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.models import Report, Exam
from app.schemas.schemas import ReportOut

router = APIRouter(prefix="/report", tags=["Report"])


@router.get("/{exam_id}", response_model=ReportOut)
async def get_report(exam_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Report).where(Report.exam_id == exam_id))
    report = result.scalar_one_or_none()

    if not report:
        exam = await db.get(Exam, exam_id)
        if not exam:
            raise HTTPException(404, "Exam not found.")
        if exam.status in ("pending", "evaluating"):
            raise HTTPException(202, f"Evaluation is {exam.status}. Try again shortly.")
        raise HTTPException(404, "Report not yet generated.")

    return report
