"""
Agent Orchestrator — coordinates the full evaluation pipeline:
  1. Extract text from stored files
  2. Run EvaluationAgent
  3. Persist Report to DB
  4. Run StudyPlanAgent
  5. Persist StudyPlan to DB
"""
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import Exam, Report, StudyPlan
from app.agents.evaluation_agent import evaluation_agent
from app.agents.study_plan_agent import study_plan_agent
from app.services.storage_service import storage_service
from app.services.vector_store import vector_store


class AgentOrchestrator:
    async def run_evaluation(
        self,
        exam_id: str,
        student_id: str,
        db: AsyncSession,
    ) -> dict:
        exam = await db.get(Exam, exam_id)
        if not exam:
            raise ValueError(f"Exam {exam_id} not found")

        exam.status = "evaluating"
        await db.commit()

        exam_text = self._load_text(exam.exam_paper_path, exam.exam_text)
        answer_text = self._load_text(exam.answer_sheet_path, exam.answer_text)

        textbook_collection = None
        if exam.textbook_id:
            from app.models.models import Textbook
            textbook = await db.get(Textbook, exam.textbook_id)
            if textbook and textbook.chroma_collection_id:
                textbook_collection = textbook.chroma_collection_id

        eval_result = await evaluation_agent.evaluate(
            exam_text=exam_text,
            answer_text=answer_text,
            textbook_collection=textbook_collection,
        )

        report = Report(
            exam_id=exam_id,
            overall_score=eval_result.get("overall_score"),
            topic_scores=eval_result.get("topic_scores"),
            weak_topics=eval_result.get("weak_topics"),
            strong_topics=eval_result.get("strong_topics"),
            answer_feedback=eval_result.get("answer_feedback"),
            summary=eval_result.get("summary"),
        )
        db.add(report)

        exam.status = "evaluated"
        exam.evaluated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(report)

        plan_result = await study_plan_agent.generate(eval_result)
        study_plan = StudyPlan(
            student_id=student_id,
            report_id=report.id,
            plan_data=plan_result,
        )
        db.add(study_plan)
        await db.commit()

        return {"report_id": report.id, "status": "complete"}

    def _load_text(self, file_path: str | None, inline_text: str | None) -> str:
        if inline_text:
            return inline_text
        if file_path:
            return storage_service.read_text_from_path(file_path)
        return ""


orchestrator = AgentOrchestrator()
