import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { ExamListItem } from '../../models/api.models';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss'],
})
export class DashboardComponent implements OnInit {
  exams: ExamListItem[] = [];
  loading = true;
  error = '';

  readonly displayedColumns = ['date', 'status', 'score', 'action'];

  get studentName(): string {
    return this.auth.student?.name ?? '';
  }

  constructor(
    private api: ApiService,
    private auth: AuthService,
    private router: Router,
    private snack: MatSnackBar
  ) {}

  ngOnInit(): void {
    const studentId = this.auth.student?.id;
    if (!studentId) {
      this.router.navigate(['/login']);
      return;
    }
    this.api.getStudentExams(studentId).subscribe({
      next: (exams) => {
        this.exams = exams;
        this.loading = false;
      },
      error: () => {
        this.error = 'Failed to load evaluations.';
        this.loading = false;
      },
    });
  }

  viewEvaluation(examId: string): void {
    this.router.navigate(['/evaluation', examId]);
  }

  scoreColor(score: number | null): string {
    if (score === null) return '#888';
    if (score >= 75) return '#2e7d32';
    if (score >= 50) return '#f57f17';
    return '#c62828';
  }

  scoreLabel(score: number | null): string {
    if (score === null) return '—';
    if (score >= 75) return 'Excellent';
    if (score >= 50) return 'Satisfactory';
    return 'Needs Improvement';
  }

  statusIcon(status: string): string {
    switch (status) {
      case 'evaluated': return 'check_circle';
      case 'evaluating': return 'hourglass_top';
      case 'pending': return 'schedule';
      default: return 'help_outline';
    }
  }

  logout(): void {
    this.auth.logout();
    this.router.navigate(['/login']);
  }
}
