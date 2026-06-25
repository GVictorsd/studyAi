from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.models import Student, Exam, Report
from app.schemas.schemas import StudentCreate, StudentOut, ExamListItem

router = APIRouter(prefix="/students", tags=["Students"])


@router.post("", response_model=StudentOut, status_code=201)
async def create_student(payload: StudentCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Student).where(Student.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(409, "A student with this email already exists.")

    student = Student(name=payload.name, email=payload.email)
    db.add(student)
    await db.commit()
    await db.refresh(student)
    return student


@router.get("/by-email/{email}", response_model=StudentOut)
async def get_student_by_email(email: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Student).where(Student.email == email))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(404, "Student not found.")
    return student


@router.get("/{student_id}", response_model=StudentOut)
async def get_student(student_id: str, db: AsyncSession = Depends(get_db)):
    student = await db.get(Student, student_id)
    if not student:
        raise HTTPException(404, "Student not found.")
    return student


@router.get("/{student_id}/exams", response_model=list[ExamListItem])
async def get_student_exams(student_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Exam).where(Exam.student_id == student_id).order_by(Exam.created_at.desc())
    )
    exams = result.scalars().all()

    items: list[ExamListItem] = []
    for exam in exams:
        report_result = await db.execute(select(Report).where(Report.exam_id == exam.id))
        report = report_result.scalar_one_or_none()
        items.append(
            ExamListItem(
                exam_id=exam.id,
                status=exam.status,
                created_at=exam.created_at,
                evaluated_at=exam.evaluated_at,
                overall_score=report.overall_score if report else None,
                report_id=report.id if report else None,
            )
        )
    return items
