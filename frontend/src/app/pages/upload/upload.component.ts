import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { UploadService } from '../../services/upload.service';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';
import { TextbookOut } from '../../models/api.models';
import { finalize } from 'rxjs/operators';

@Component({
  selector: 'app-upload',
  templateUrl: './upload.component.html',
  styleUrls: ['./upload.component.scss'],
})
export class UploadComponent implements OnInit {
  examForm: FormGroup;

  examFile: File | null = null;
  answerFile: File | null = null;

  examId = '';
  selectedTextbookId = '';

  textbooks: TextbookOut[] = [];
  loadingTextbooks = true;

  uploadingExam = false;
  evaluating = false;
  examDone = false;

  get studentId(): string {
    return this.auth.student?.id ?? '';
  }

  constructor(
    private fb: FormBuilder,
    private uploadSvc: UploadService,
    private apiSvc: ApiService,
    private auth: AuthService,
    private snack: MatSnackBar,
    private router: Router
  ) {
    this.examForm = this.fb.group({
      examText: [''],
      answerText: [''],
    });
  }

  ngOnInit(): void {
    this.apiSvc.getTextbooks().subscribe({
      next: (list) => {
        this.textbooks = list;
        this.loadingTextbooks = false;
      },
      error: () => (this.loadingTextbooks = false),
    });
  }

  onExamFile(e: Event): void {
    this.examFile = (e.target as HTMLInputElement).files?.[0] ?? null;
  }

  onAnswerFile(e: Event): void {
    this.answerFile = (e.target as HTMLInputElement).files?.[0] ?? null;
  }

  submitExam(): void {
    const { examText, answerText } = this.examForm.value;
    if (!this.examFile && !examText?.trim()) {
      this.snack.open('Provide an exam paper file or paste exam text.', 'OK', { duration: 3000 });
      return;
    }
    if (!this.answerFile && !answerText?.trim()) {
      this.snack.open('Provide an answer sheet file or paste answer text.', 'OK', { duration: 3000 });
      return;
    }

    this.uploadingExam = true;
    this.uploadSvc
      .uploadExamPaper(
        this.studentId,
        this.selectedTextbookId || undefined,
        this.examFile ?? undefined,
        examText || undefined
      )
      .subscribe({
        next: (r) => {
          this.examId = r.exam_id;
          this.uploadSvc
            .uploadAnswers(this.examId, this.answerFile ?? undefined, answerText || undefined)
            .pipe(finalize(() => (this.uploadingExam = false)))
            .subscribe({
              next: () => {
                this.examDone = true;
                this.snack.open('Exam and answers saved!', 'OK', { duration: 3000 });
              },
              error: () => this.snack.open('Answer upload failed.', 'Dismiss', { duration: 4000 }),
            });
        },
        error: () => {
          this.uploadingExam = false;
          this.snack.open('Exam upload failed.', 'Dismiss', { duration: 4000 });
        },
      });
  }

  startEvaluation(): void {
    this.evaluating = true;
    this.apiSvc
      .evaluate({ exam_id: this.examId, student_id: this.studentId })
      .pipe(finalize(() => (this.evaluating = false)))
      .subscribe({
        next: () => {
          this.snack.open('Evaluation started! Redirecting to dashboard…', 'OK', { duration: 3000 });
          setTimeout(() => this.router.navigate(['/dashboard']), 2500);
        },
        error: () => this.snack.open('Failed to start evaluation.', 'Dismiss', { duration: 4000 }),
      });
  }
}
