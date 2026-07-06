from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from app.db.database import get_db
from app.models.models import StudyPlan, StudentMistakeContext, Exam, Report
from app.schemas.schemas import StudyPlanOut
from app.agents.study_plan_agent import generate as generate_study_plan

router = APIRouter(prefix="/study-plan", tags=["Study Plan"])


async def _fetch_mistake_context(student_id: str, db: AsyncSession) -> dict | None:
    result = await db.execute(
        select(StudentMistakeContext).where(StudentMistakeContext.student_id == student_id)
    )
    row = result.scalar_one_or_none()
    return row.context_data if row else None


@router.get("/{student_id}", response_model=StudyPlanOut)
async def get_study_plan(student_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StudyPlan)
        .where(StudyPlan.student_id == student_id)
        .order_by(StudyPlan.generated_at.desc())
        .limit(1)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(404, "No study plan found for this student.")

    return plan


@router.get("/{student_id}/global", response_model=StudyPlanOut)
async def get_global_study_plan(student_id: str, db: AsyncSession = Depends(get_db)):
    """Returns the latest global study plan (not tied to a specific exam)."""
    result = await db.execute(
        select(StudyPlan)
        .where(StudyPlan.student_id == student_id, StudyPlan.report_id == None)  # noqa: E711
        .order_by(StudyPlan.generated_at.desc())
        .limit(1)
    )
    plan = result.scalar_one_or_none()

    if not plan:
        raise HTTPException(404, "No global study plan found. Refresh to generate.")

    return plan


@router.post("/{student_id}/refresh", response_model=StudyPlanOut)
async def refresh_global_study_plan(student_id: str, db: AsyncSession = Depends(get_db)):
    """Regenerates a comprehensive global study plan from all accumulated exam context."""
    exams_result = await db.execute(
        select(Exam)
        .where(Exam.student_id == student_id, Exam.status == "evaluated")
        .order_by(Exam.evaluated_at.asc())
    )
    exams = exams_result.scalars().all()

    if not exams:
        raise HTTPException(400, "No evaluated exams found. Complete an evaluation first.")

    all_weak: list[str] = []
    all_strong: list[str] = []
    all_summaries: list[str] = []
    total_score = 0.0
    count = 0

    for exam in exams:
        report_result = await db.execute(
            select(Report).where(Report.exam_id == exam.id)
        )
        report = report_result.scalar_one_or_none()
        if report:
            all_weak.extend(report.weak_topics or [])
            all_strong.extend(report.strong_topics or [])
            if report.summary:
                all_summaries.append(report.summary)
            if report.overall_score is not None:
                total_score += report.overall_score
                count += 1

    unique_weak = list(dict.fromkeys(all_weak))
    unique_strong = list(dict.fromkeys(all_strong))
    avg_score = round(total_score / count, 1) if count else 0

    aggregated_report = {
        "overall_score": avg_score,
        "weak_topics": unique_weak,
        "strong_topics": unique_strong,
        "summary": " ".join(all_summaries[-3:]),
    }

    mistake_context = await _fetch_mistake_context(student_id, db)

    plan_result = await generate_study_plan(
        report=aggregated_report,
        mistake_context=mistake_context,
    )

    new_plan = StudyPlan(
        student_id=student_id,
        report_id=None,
        plan_data=plan_result,
        generated_at=datetime.utcnow(),
    )
    db.add(new_plan)
    await db.commit()
    await db.refresh(new_plan)
    return new_plan
