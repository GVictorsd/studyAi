from pydantic import BaseModel, EmailStr
from typing import Any
from datetime import datetime


# ── Student ──────────────────────────────────────────────────────────────────

class StudentCreate(BaseModel):
    name: str
    email: EmailStr


class StudentOut(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Textbook ──────────────────────────────────────────────────────────────────

class TextbookOut(BaseModel):
    id: str
    title: str
    is_indexed: bool
    uploaded_at: datetime

    model_config = {"from_attributes": True}


# ── Exam list ────────────────────────────────────────────────────────────────

class ExamListItem(BaseModel):
    exam_id: str
    status: str
    created_at: datetime
    evaluated_at: datetime | None
    overall_score: float | None
    report_id: str | None

    model_config = {"from_attributes": True}


# ── Upload responses ──────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    id: str
    filename: str
    message: str


class ExamUploadResponse(BaseModel):
    exam_id: str
    message: str


# ── Evaluate ──────────────────────────────────────────────────────────────────

class EvaluateRequest(BaseModel):
    exam_id: str
    student_id: str


class EvaluateResponse(BaseModel):
    exam_id: str
    status: str
    message: str


# ── Report ────────────────────────────────────────────────────────────────────

class AnswerFeedback(BaseModel):
    question: str
    student_answer: str
    correct_answer: str | None
    score: float
    feedback: str
    topic: str


class ReportOut(BaseModel):
    id: str
    exam_id: str
    overall_score: float | None
    topic_scores: dict[str, float] | None
    weak_topics: list[str] | None
    strong_topics: list[str] | None
    answer_feedback: list[dict[str, Any]] | None
    summary: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Study Plan ────────────────────────────────────────────────────────────────

class StudyPlanOut(BaseModel):
    id: str
    student_id: str
    report_id: str | None
    plan_data: dict[str, Any] | None
    generated_at: datetime

    model_config = {"from_attributes": True}
