from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.models import StudyPlan
from app.schemas.schemas import StudyPlanOut

router = APIRouter(prefix="/study-plan", tags=["Study Plan"])


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
