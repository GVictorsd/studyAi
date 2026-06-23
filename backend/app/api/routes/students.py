from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.database import get_db
from app.models.models import Student
from app.schemas.schemas import StudentCreate, StudentOut

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


@router.get("/{student_id}", response_model=StudentOut)
async def get_student(student_id: str, db: AsyncSession = Depends(get_db)):
    student = await db.get(Student, student_id)
    if not student:
        raise HTTPException(404, "Student not found.")
    return student
