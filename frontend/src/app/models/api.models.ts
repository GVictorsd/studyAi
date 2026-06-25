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

export interface AnswerFeedback {
  question: string;
  student_answer: string;
  correct_answer: string;
  score: number;
  feedback: string;
  topic: string;
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

export interface WeeklyGoal {
  week: number;
  focus_topics: string[];
  daily_tasks: { day: string; tasks: string[] }[];
  milestone: string;
}

export interface StudyPlanOut {
  id: string;
  student_id: string;
  report_id: string;
  plan_data: {
    duration_weeks: number;
    weekly_goals: WeeklyGoal[];
    resources: { topic: string; suggestions: string[] }[];
    tips: string[];
  };
  generated_at: string;
}
