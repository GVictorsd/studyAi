import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { ChartData, ChartOptions } from 'chart.js';
import { ApiService } from '../../services/api.service';
import { ReportOut, StudyPlanOut, StudentOut } from '../../models/api.models';
import { interval, Subscription } from 'rxjs';
import { switchMap, takeWhile } from 'rxjs/operators';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss'],
})
export class DashboardComponent implements OnInit {
  studentId = '';
  examId = '';

  student: StudentOut | null = null;
  report: ReportOut | null = null;
  studyPlan: StudyPlanOut | null = null;

  loading = true;
  polling = false;
  error = '';

  activeTab = 0;

  // Chart data
  radarChartData: ChartData<'radar'> = { labels: [], datasets: [] };
  barChartData: ChartData<'bar'> = { labels: [], datasets: [] };

  radarChartOptions: ChartOptions<'radar'> = {
    responsive: true,
    scales: {
      r: {
        min: 0,
        max: 100,
        ticks: { stepSize: 20 },
      },
    },
    plugins: { legend: { display: false } },
  };

  barChartOptions: ChartOptions<'bar'> = {
    responsive: true,
    plugins: {
      legend: { display: false },
      tooltip: { callbacks: { label: (ctx) => `${(ctx.parsed.y ?? 0).toFixed(1)}%` } },
    },
    scales: {
      y: { min: 0, max: 100, ticks: { callback: (v) => `${v}%` } },
    },
  };

  private pollSub?: Subscription;

  constructor(private route: ActivatedRoute, private apiSvc: ApiService) {}

  ngOnInit(): void {
    this.studentId = this.route.snapshot.paramMap.get('studentId') ?? '';
    this.examId = this.route.snapshot.queryParamMap.get('examId') ?? '';

    if (this.studentId) {
      this.loadStudent();
      this.loadReport();
      this.loadStudyPlan();
    }
  }

  private loadStudent(): void {
    this.apiSvc.getStudent(this.studentId).subscribe({
      next: (s) => (this.student = s),
      error: () => {},
    });
  }

  private loadReport(): void {
    this.loading = true;
    if (this.examId) {
      this.tryFetchReport(this.examId);
    } else {
      this.loading = false;
    }
  }

  private tryFetchReport(examId: string): void {
    this.polling = true;
    let attempts = 0;
    this.pollSub = interval(5000)
      .pipe(
        switchMap(() => this.apiSvc.getReport(examId)),
        takeWhile((report) => !report || attempts++ < 24, true)
      )
      .subscribe({
        next: (report) => {
          if (report && report.id) {
            this.report = report;
            this.buildCharts(report);
            this.polling = false;
            this.loading = false;
            this.pollSub?.unsubscribe();
          }
        },
        error: (err) => {
          if (err.status !== 202 && err.status !== 404) {
            this.error = 'Failed to load report.';
            this.polling = false;
            this.loading = false;
          }
        },
      });
  }

  private loadStudyPlan(): void {
    this.apiSvc.getStudyPlan(this.studentId).subscribe({
      next: (plan) => (this.studyPlan = plan),
      error: () => {},
    });
  }

  private buildCharts(report: ReportOut): void {
    const topics = Object.keys(report.topic_scores ?? {});
    const scores = topics.map((t) => report.topic_scores![t]);

    this.radarChartData = {
      labels: topics,
      datasets: [
        {
          data: scores,
          label: 'Score %',
          backgroundColor: 'rgba(63, 81, 181, 0.15)',
          borderColor: '#3f51b5',
          pointBackgroundColor: '#3f51b5',
        },
      ],
    };

    const bgColors = scores.map((s) =>
      s >= 80 ? '#43a047' : s >= 60 ? '#fb8c00' : '#e53935'
    );

    this.barChartData = {
      labels: topics,
      datasets: [
        {
          data: scores,
          label: 'Score %',
          backgroundColor: bgColors,
          borderRadius: 6,
        },
      ],
    };
  }

  get scoreColor(): string {
    if (!this.report) return '#999';
    const s = this.report.overall_score;
    return s >= 80 ? '#2e7d32' : s >= 60 ? '#e65100' : '#c62828';
  }

  get scoreLabel(): string {
    if (!this.report) return '';
    const s = this.report.overall_score;
    return s >= 80 ? 'Excellent' : s >= 60 ? 'Satisfactory' : 'Needs Improvement';
  }

  ngOnDestroy(): void {
    this.pollSub?.unsubscribe();
  }
}
