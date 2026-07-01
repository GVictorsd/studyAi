import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { InsightsOut, InsightsData } from '../../models/api.models';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-insights',
  templateUrl: './insights.component.html',
  styleUrls: ['./insights.component.scss'],
})
export class InsightsComponent implements OnInit {
  insights: InsightsOut | null = null;
  insightsData: InsightsData | null = null;
  loading = false;
  refreshing = false;
  studentId: string | null = null;

  readonly trendConfig: Record<string, { icon: string; label: string; color: string }> = {
    improving:         { icon: 'trending_up',    label: 'Improving',          color: '#4caf50' },
    declining:         { icon: 'trending_down',  label: 'Declining',          color: '#f44336' },
    stable:            { icon: 'trending_flat',  label: 'Stable',             color: '#ff9800' },
    insufficient_data: { icon: 'hourglass_empty',label: 'Not Enough Data',    color: '#9e9e9e' },
  };

  constructor(
    private api: ApiService,
    private auth: AuthService,
    private snack: MatSnackBar,
  ) {}

  ngOnInit(): void {
    const student = this.auth.student;
    if (student) {
      this.studentId = student.id;
      this.loadInsights();
    }
  }

  loadInsights(): void {
    if (!this.studentId) return;
    this.loading = true;
    this.api.getInsights(this.studentId).subscribe({
      next: (res) => {
        this.insights = res;
        this.insightsData = res.insights_data;
        this.loading = false;
      },
      error: (err) => {
        if (err.status !== 404) {
          this.snack.open('Failed to load insights.', 'Dismiss', { duration: 3000 });
        }
        this.loading = false;
      },
    });
  }

  refresh(): void {
    if (!this.studentId) return;
    this.refreshing = true;
    this.api.refreshInsights(this.studentId).subscribe({
      next: (res) => {
        this.insights = res;
        this.insightsData = res.insights_data;
        this.refreshing = false;
        this.snack.open('Insights updated!', 'Close', { duration: 3000 });
      },
      error: () => {
        this.refreshing = false;
        this.snack.open('Failed to generate insights. Ensure you have completed evaluations.', 'Dismiss', { duration: 5000 });
      },
    });
  }

  get trendInfo() {
    const trend = this.insightsData?.score_trend ?? 'insufficient_data';
    return this.trendConfig[trend] ?? this.trendConfig['insufficient_data'];
  }

  get scorePercent(): number {
    return Math.min(100, Math.max(0, this.insightsData?.average_score ?? 0));
  }

  get scoreColor(): string {
    const s = this.scorePercent;
    if (s >= 75) return 'primary';
    if (s >= 50) return 'accent';
    return 'warn';
  }

  get readinessColor(): string {
    const r = this.insightsData?.readiness_score ?? 0;
    if (r >= 70) return '#4caf50';
    if (r >= 50) return '#ff9800';
    return '#f44336';
  }

  rawScoreColor(score: number): string {
    if (score >= 75) return '#2e7d32';
    if (score >= 50) return '#f57f17';
    return '#c62828';
  }
}
