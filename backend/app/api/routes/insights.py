from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.db.database import get_db
from app.models.models import StudentInsights, StudentMistakeContext, Exam, Report
from app.schemas.schemas import InsightsOut
from app.agents.insights_agent import insights_agent

router = APIRouter(prefix="/insights", tags=["Insights"])


async def _fetch_mistake_context(student_id: str, db: AsyncSession) -> dict | None:
    result = await db.execute(
        select(StudentMistakeContext).where(StudentMistakeContext.student_id == student_id)
    )
    row = result.scalar_one_or_none()
    return row.context_data if row else None


@router.get("/{student_id}", response_model=InsightsOut)
async def get_insights(student_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StudentInsights).where(StudentInsights.student_id == student_id)
    )
    insights = result.scalar_one_or_none()

    if not insights:
        raise HTTPException(404, "No insights found. Refresh to generate.")

    return insights


@router.post("/{student_id}/refresh", response_model=InsightsOut)
async def refresh_insights(student_id: str, db: AsyncSession = Depends(get_db)):
    exams_result = await db.execute(
        select(Exam)
        .where(Exam.student_id == student_id, Exam.status == "evaluated")
        .order_by(Exam.evaluated_at.asc())
    )
    exams = exams_result.scalars().all()

    reports_data: list[dict] = []
    for exam in exams:
        report_result = await db.execute(
            select(Report).where(Report.exam_id == exam.id)
        )
        report = report_result.scalar_one_or_none()
        if report:
            reports_data.append({
                "date": exam.evaluated_at.isoformat() if exam.evaluated_at else "",
                "overall_score": report.overall_score,
                "weak_topics": report.weak_topics or [],
                "strong_topics": report.strong_topics or [],
                "topic_scores": report.topic_scores or {},
                "summary": report.summary or "",
            })

    mistake_context = await _fetch_mistake_context(student_id, db)
    generated = await insights_agent.generate(reports_data, mistake_context=mistake_context)

    existing_result = await db.execute(
        select(StudentInsights).where(StudentInsights.student_id == student_id)
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        existing.insights_data = generated
        existing.generated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(existing)
        return existing

    new_insights = StudentInsights(
        student_id=student_id,
        insights_data=generated,
    )
    db.add(new_insights)
    await db.commit()
    await db.refresh(new_insights)
    return new_insights
