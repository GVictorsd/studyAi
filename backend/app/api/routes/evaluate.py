from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.schemas import EvaluateRequest, EvaluateResponse
from app.agents.orchestrator import orchestrator

router = APIRouter(prefix="/evaluate", tags=["Evaluate"])


@router.post("", response_model=EvaluateResponse)
async def evaluate_exam(
    payload: EvaluateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    background_tasks.add_task(
        orchestrator.run_evaluation,
        exam_id=payload.exam_id,
        student_id=payload.student_id,
        db=db,
    )
    return EvaluateResponse(
        exam_id=payload.exam_id,
        status="processing",
        message="Evaluation started. Fetch /report/{examId} once complete.",
    )
