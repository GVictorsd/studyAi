"""
Agent Orchestrator — coordinates the full evaluation pipeline:
  1. Extract text from stored files
  2. Parse individual questions from the exam
  3. TextbookKnowledgeAgent: retrieve per-question context
  4. EvaluationAgent: rubric-based per-question evaluation
  5. Persist Report to DB
  6. MistakeAnalysisAgent: update accumulated mistake context (background)
  7. TextbookKnowledgeAgent: retrieve per-weak-topic references
  8. StudyPlanAgent: generate mistake-aware personalised plan
  9. Persist StudyPlan to DB
"""
import re
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.evaluation_agent import evaluation_agent
from app.agents.mistake_analysis_agent import mistake_analysis_agent
from app.agents.study_plan_agent import study_plan_agent
from app.agents.textbook_knowledge_agent import textbook_knowledge_agent, KnowledgeResult
from app.models.models import Exam, Report, StudyPlan, StudentMistakeContext
from app.services.storage_service import storage_service


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

        textbook_collection: str | None = None
        if exam.textbook_id:
            from app.models.models import Textbook
            textbook = await db.get(Textbook, exam.textbook_id)
            if textbook and textbook.chroma_collection_id:
                textbook_collection = textbook.chroma_collection_id

        # --- Per-question retrieval ---
        knowledge_results: list[KnowledgeResult] = []
        if textbook_collection:
            questions = self._extract_questions(exam_text)
            knowledge_results = textbook_knowledge_agent.retrieve_for_questions(
                questions=questions,
                collection_name=textbook_collection,
                n_results=3,
            )

        # --- Rubric-based evaluation ---
        eval_result = await evaluation_agent.evaluate(
            exam_text=exam_text,
            answer_text=answer_text,
            knowledge_results=knowledge_results or None,
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

        # --- Update mistake context ---
        existing_ctx_result = await db.execute(
            select(StudentMistakeContext).where(
                StudentMistakeContext.student_id == student_id
            )
        )
        existing_ctx_row = existing_ctx_result.scalar_one_or_none()
        existing_ctx_data = existing_ctx_row.context_data if existing_ctx_row else None

        updated_ctx = await mistake_analysis_agent.update_context(
            new_report=eval_result,
            existing_context=existing_ctx_data,
        )

        if existing_ctx_row:
            existing_ctx_row.context_data = updated_ctx
            existing_ctx_row.exam_count = updated_ctx.get("total_exams_analyzed", existing_ctx_row.exam_count + 1)
            existing_ctx_row.last_updated = datetime.utcnow()
        else:
            db.add(StudentMistakeContext(
                student_id=student_id,
                context_data=updated_ctx,
                exam_count=updated_ctx.get("total_exams_analyzed", 1),
            ))
        await db.commit()

        # --- Per-weak-topic retrieval for study plan ---
        textbook_refs: dict[str, KnowledgeResult] = {}
        if textbook_collection:
            for topic in eval_result.get("weak_topics") or []:
                textbook_refs[topic] = textbook_knowledge_agent.retrieve(
                    query=topic,
                    collection_name=textbook_collection,
                    n_results=2,
                )

        # --- Mistake-aware study plan ---
        plan_result = await study_plan_agent.generate(
            report=eval_result,
            textbook_references=textbook_refs or None,
            mistake_context=updated_ctx,
        )

        study_plan = StudyPlan(
            student_id=student_id,
            report_id=report.id,
            plan_data=plan_result,
        )
        db.add(study_plan)
        await db.commit()

        return {"report_id": report.id, "status": "complete"}

    def _extract_questions(self, exam_text: str) -> list[str]:
        pattern = re.compile(
            r'(?m)^[ \t]*(?:Q\.?\s*\d+|Question\s+\d+|\d+)[.):][ \t]*'
            r'(.+?)(?=^[ \t]*(?:Q\.?\s*\d+|Question\s+\d+|\d+)[.):][ \t]|\Z)',
            re.DOTALL | re.IGNORECASE,
        )
        matches = [m.group(1).strip() for m in pattern.finditer(exam_text)]
        questions = [q for q in matches if len(q) > 10]
        return questions if questions else [exam_text]

    def _load_text(self, file_path: str | None, inline_text: str | None) -> str:
        if inline_text:
            return inline_text
        if file_path:
            return storage_service.read_text_from_path(file_path)
        return ""


orchestrator = AgentOrchestrator()
