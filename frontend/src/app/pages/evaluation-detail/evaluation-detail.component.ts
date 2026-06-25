import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService } from '../../services/api.service';
import { ReportOut, StudyPlanOut, AnswerFeedback } from '../../models/api.models';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-evaluation-detail',
  templateUrl: './evaluation-detail.component.html',
  styleUrls: ['./evaluation-detail.component.scss'],
})
export class EvaluationDetailComponent implements OnInit {
  examId = '';
  report: ReportOut | null = null;
  studyPlan: StudyPlanOut | null = null;
  loading = true;
  error = '';

  readonly feedbackColumns = ['question', 'topic', 'score', 'feedback'];
  readonly topicColumns = ['topic', 'score', 'level'];

  get topicRows(): { topic: string; score: number }[] {
    if (!this.report?.topic_scores) return [];
    return Object.entries(this.report.topic_scores).map(([topic, score]) => ({ topic, score }));
  }

  get feedbackRows(): AnswerFeedback[] {
    return (this.report?.answer_feedback as AnswerFeedback[]) ?? [];
  }

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private api: ApiService,
    private auth: AuthService
  ) {}

  ngOnInit(): void {
    this.examId = this.route.snapshot.paramMap.get('examId') ?? '';
    if (!this.examId) {
      this.router.navigate(['/dashboard']);
      return;
    }
    this.api.getReport(this.examId).subscribe({
      next: (report) => {
        this.report = report;
        this.loading = false;
        const studentId = this.auth.student?.id;
        if (studentId) {
          this.api.getStudyPlan(studentId).subscribe({
            next: (plan) => (this.studyPlan = plan),
            error: () => {},
          });
        }
      },
      error: (err) => {
        if (err.status === 202) {
          this.error = 'Evaluation is still processing. Please check back shortly.';
        } else {
          this.error = 'Failed to load the report.';
        }
        this.loading = false;
      },
    });
  }

  scoreColor(score: number): string {
    if (score >= 75) return '#2e7d32';
    if (score >= 50) return '#f57f17';
    return '#c62828';
  }

  scoreLevel(score: number): string {
    if (score >= 75) return 'Excellent';
    if (score >= 50) return 'Satisfactory';
    return 'Needs Improvement';
  }

  goBack(): void {
    this.router.navigate(['/dashboard']);
  }
}
