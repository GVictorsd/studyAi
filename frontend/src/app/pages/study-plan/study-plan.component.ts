import { Component, OnInit } from '@angular/core';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { StudyPlanOut, WeeklyGoal } from '../../models/api.models';
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-study-plan',
  templateUrl: './study-plan.component.html',
  styleUrls: ['./study-plan.component.scss'],
})
export class StudyPlanPageComponent implements OnInit {
  plan: StudyPlanOut | null = null;
  loading = false;
  refreshing = false;
  studentId: string | null = null;

  constructor(
    private api: ApiService,
    private auth: AuthService,
    private snack: MatSnackBar,
  ) {}

  ngOnInit(): void {
    const student = this.auth.student;
    if (student) {
      this.studentId = student.id;
      this.loadPlan();
    }
  }

  loadPlan(): void {
    if (!this.studentId) return;
    this.loading = true;
    this.api.getGlobalStudyPlan(this.studentId).subscribe({
      next: (res) => {
        this.plan = res;
        this.loading = false;
      },
      error: (err) => {
        if (err.status !== 404) {
          this.snack.open('Failed to load study plan.', 'Dismiss', { duration: 3000 });
        }
        this.loading = false;
      },
    });
  }

  refresh(): void {
    if (!this.studentId) return;
    this.refreshing = true;
    this.api.refreshGlobalStudyPlan(this.studentId).subscribe({
      next: (res) => {
        this.plan = res;
        this.refreshing = false;
        this.snack.open('Study plan updated!', 'Close', { duration: 3000 });
      },
      error: () => {
        this.refreshing = false;
        this.snack.open('Failed to generate plan. Ensure you have completed evaluations.', 'Dismiss', { duration: 5000 });
      },
    });
  }

  get weeklyGoals(): WeeklyGoal[] {
    return this.plan?.plan_data?.weekly_goals ?? [];
  }

  get resources() {
    return this.plan?.plan_data?.resources ?? [];
  }

  get tips(): string[] {
    return this.plan?.plan_data?.tips ?? [];
  }

  get durationWeeks(): number {
    return this.plan?.plan_data?.duration_weeks ?? 0;
  }
}
