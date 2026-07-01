import uuid
from datetime import datetime
from sqlalchemy import String, Float, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    exams: Mapped[list["Exam"]] = relationship("Exam", back_populates="student")
    study_plans: Mapped[list["StudyPlan"]] = relationship("StudyPlan", back_populates="student")
    insights: Mapped["StudentInsights | None"] = relationship("StudentInsights", back_populates="student", uselist=False)
    mistake_context: Mapped["StudentMistakeContext | None"] = relationship("StudentMistakeContext", back_populates="student", uselist=False)


class Textbook(Base):
    __tablename__ = "textbooks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    chroma_collection_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_indexed: Mapped[bool] = mapped_column(default=False)

    exams: Mapped[list["Exam"]] = relationship("Exam", back_populates="textbook")


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    textbook_id: Mapped[str | None] = mapped_column(ForeignKey("textbooks.id"), nullable=True)
    exam_paper_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    answer_sheet_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    exam_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    student: Mapped["Student"] = relationship("Student", back_populates="exams")
    textbook: Mapped["Textbook | None"] = relationship("Textbook", back_populates="exams")
    report: Mapped["Report | None"] = relationship("Report", back_populates="exam", uselist=False)


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    exam_id: Mapped[str] = mapped_column(ForeignKey("exams.id"), unique=True, nullable=False)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    topic_scores: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    weak_topics: Mapped[list | None] = mapped_column(JSON, nullable=True)
    strong_topics: Mapped[list | None] = mapped_column(JSON, nullable=True)
    answer_feedback: Mapped[list | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    exam: Mapped["Exam"] = relationship("Exam", back_populates="report")


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), nullable=False)
    report_id: Mapped[str | None] = mapped_column(ForeignKey("reports.id"), nullable=True)
    plan_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    student: Mapped["Student"] = relationship("Student", back_populates="study_plans")


class StudentMistakeContext(Base):
    """Accumulated error-pattern context, updated after every evaluated exam."""
    __tablename__ = "student_mistake_context"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), unique=True, nullable=False)
    context_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    exam_count: Mapped[int] = mapped_column(default=0)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    student: Mapped["Student"] = relationship("Student", back_populates="mistake_context")


class StudentInsights(Base):
    """Accumulated performance insights across all evaluated exams for a student."""
    __tablename__ = "student_insights"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=gen_uuid)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), unique=True, nullable=False)
    insights_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    student: Mapped["Student"] = relationship("Student", back_populates="insights")
