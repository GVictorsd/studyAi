export interface StudentCreate {
  name: string;
  email: string;
}

export interface StudentOut {
  id: string;
  name: string;
  email: string;
  created_at: string;
}

export interface TextbookOut {
  id: string;
  title: string;
  is_indexed: boolean;
  uploaded_at: string;
}

export interface ExamListItem {
  exam_id: string;
  status: string;
  created_at: string;
  evaluated_at: string | null;
  overall_score: number | null;
  report_id: string | null;
}

export interface UploadResponse {
  id: string;
  filename: string;
  message: string;
}

export interface ExamUploadResponse {
  exam_id: string;
  message: string;
}

export interface EvaluateRequest {
  exam_id: string;
  student_id: string;
}

export interface EvaluateResponse {
  exam_id: string;
  status: string;
  message: string;
}

// ── Rubric ───────────────────────────────────────────────────────────────────

export interface RubricMetric {
  score: number;
  comment: string;
}

export interface AnswerRubric {
  correctness: RubricMetric;
  completeness: RubricMetric;
  conceptual_accuracy: RubricMetric;
  writing_quality: RubricMetric;
}

export interface AnswerFeedback {
  question: string;
  student_answer: string;
  correct_answer: string;
  topic: string;
  question_type: 'numerical' | 'theory' | 'derivation' | 'definition' | null;
  score: number;
  feedback: string;
  rubric: AnswerRubric | null;
  missing_steps: string[] | null;
}

export interface ReportOut {
  id: string;
  exam_id: string;
  overall_score: number;
  topic_scores: Record<string, number>;
  weak_topics: string[];
  strong_topics: string[];
  answer_feedback: AnswerFeedback[];
  summary: string;
  created_at: string;
}

// ── Study Plan ───────────────────────────────────────────────────────────────

export interface WeeklyGoal {
  week: number;
  focus_topics: string[];
  daily_tasks: { day: string; tasks: string[] }[];
  milestone: string;
}

export interface StudyPlanOut {
  id: string;
  student_id: string;
  report_id: string | null;
  plan_data: {
    duration_weeks: number;
    weekly_goals: WeeklyGoal[];
    resources: { topic: string; chapter_reference?: string | null; suggestions: string[] }[];
    tips: string[];
  } | null;
  generated_at: string;
}

// ── Insights ─────────────────────────────────────────────────────────────────

export interface InsightsData {
  average_score: number | null;
  score_trend: 'improving' | 'declining' | 'stable' | 'insufficient_data';
  strongest_area: string | null;
  weakest_area: string | null;
  numerical_accuracy: number | null;
  theory_accuracy: number | null;
  readiness_score: number | null;
  consistently_weak_topics: string[];
  consistently_strong_topics: string[];
  improving_topics: string[];
  declining_topics: string[];
  recurring_mistakes: string[];
  overall_summary: string;
  key_insights: string[];
  recommendations: string[];
}

export interface InsightsOut {
  id: string;
  student_id: string;
  insights_data: InsightsData | null;
  generated_at: string;
}
