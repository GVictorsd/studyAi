import { Component } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { UploadService } from '../../services/upload.service';
import { ApiService } from '../../services/api.service';
import { finalize } from 'rxjs/operators';

interface StepStatus {
  student: 'pending' | 'done';
  textbook: 'pending' | 'uploading' | 'done';
  exam: 'pending' | 'uploading' | 'done';
  answers: 'pending' | 'uploading' | 'done';
  evaluate: 'pending' | 'processing' | 'done';
}

@Component({
  selector: 'app-upload',
  templateUrl: './upload.component.html',
  styleUrls: ['./upload.component.scss'],
})
export class UploadComponent {
  studentForm: FormGroup;
  textbookTitleForm: FormGroup;

  studentId = '';
  textbookId = '';
  examId = '';

  textbookFile: File | null = null;
  examFile: File | null = null;
  answerFile: File | null = null;
  examText = '';
  answerText = '';

  status: StepStatus = {
    student: 'pending',
    textbook: 'pending',
    exam: 'pending',
    answers: 'pending',
    evaluate: 'pending',
  };

  constructor(
    private fb: FormBuilder,
    private uploadSvc: UploadService,
    private apiSvc: ApiService,
    private snack: MatSnackBar,
    private router: Router
  ) {
    this.studentForm = this.fb.group({
      name: ['', [Validators.required, Validators.minLength(2)]],
      email: ['', [Validators.required, Validators.email]],
    });
    this.textbookTitleForm = this.fb.group({
      title: ['', Validators.required],
    });
  }

  // ── File selectors ─────────────────────────────────────────────────────────

  onTextbookFile(e: Event) {
    const input = e.target as HTMLInputElement;
    this.textbookFile = input.files?.[0] ?? null;
  }

  onExamFile(e: Event) {
    const input = e.target as HTMLInputElement;
    this.examFile = input.files?.[0] ?? null;
  }

  onAnswerFile(e: Event) {
    const input = e.target as HTMLInputElement;
    this.answerFile = input.files?.[0] ?? null;
  }

  // ── Step 1: Register student ───────────────────────────────────────────────

  registerStudent() {
    if (this.studentForm.invalid) return;
    this.apiSvc.createStudent(this.studentForm.value).subscribe({
      next: (s) => {
        this.studentId = s.id;
        this.status.student = 'done';
        this.snack.open(`Welcome, ${s.name}!`, 'OK', { duration: 3000 });
      },
      error: (err) => {
        const msg = err.error?.detail ?? 'Failed to register student.';
        this.snack.open(msg, 'Dismiss', { duration: 4000 });
      },
    });
  }

  // ── Step 2: Upload textbook ────────────────────────────────────────────────

  uploadTextbook() {
    if (!this.textbookFile || this.textbookTitleForm.invalid) return;
    this.status.textbook = 'uploading';
    this.uploadSvc
      .uploadTextbook(this.textbookFile, this.textbookTitleForm.value.title)
      .pipe(finalize(() => {}))
      .subscribe({
        next: (r) => {
          this.textbookId = r.id;
          this.status.textbook = 'done';
          this.snack.open('Textbook uploaded & indexed!', 'OK', { duration: 3000 });
        },
        error: () => {
          this.status.textbook = 'pending';
          this.snack.open('Textbook upload failed.', 'Dismiss', { duration: 4000 });
        },
      });
  }

  // ── Step 3: Upload exam paper ─────────────────────────────────────────────

  uploadExam() {
    if (!this.examFile && !this.examText.trim()) {
      this.snack.open('Please provide an exam paper (file or text).', 'OK', { duration: 3000 });
      return;
    }
    this.status.exam = 'uploading';
    this.uploadSvc
      .uploadExamPaper(
        this.studentId,
        this.textbookId,
        this.examFile ?? undefined,
        this.examText || undefined
      )
      .subscribe({
        next: (r) => {
          this.examId = r.exam_id;
          this.status.exam = 'done';
          this.snack.open('Exam paper saved!', 'OK', { duration: 3000 });
        },
        error: () => {
          this.status.exam = 'pending';
          this.snack.open('Exam upload failed.', 'Dismiss', { duration: 4000 });
        },
      });
  }

  // ── Step 4: Upload answers ────────────────────────────────────────────────

  uploadAnswers() {
    if (!this.answerFile && !this.answerText.trim()) {
      this.snack.open('Please provide an answer sheet (file or text).', 'OK', { duration: 3000 });
      return;
    }
    this.status.answers = 'uploading';
    this.uploadSvc
      .uploadAnswers(
        this.examId,
        this.answerFile ?? undefined,
        this.answerText || undefined
      )
      .subscribe({
        next: () => {
          this.status.answers = 'done';
          this.snack.open('Answers saved!', 'OK', { duration: 3000 });
        },
        error: () => {
          this.status.answers = 'pending';
          this.snack.open('Answer upload failed.', 'Dismiss', { duration: 4000 });
        },
      });
  }

  // ── Step 5: Evaluate ──────────────────────────────────────────────────────

  evaluate() {
    this.status.evaluate = 'processing';
    this.apiSvc
      .evaluate({ exam_id: this.examId, student_id: this.studentId })
      .subscribe({
        next: () => {
          this.status.evaluate = 'done';
          this.snack.open(
            'Evaluation started! Redirecting to dashboard…',
            'OK',
            { duration: 3000 }
          );
          setTimeout(() => this.router.navigate(['/dashboard', this.studentId]), 2500);
        },
        error: () => {
          this.status.evaluate = 'pending';
          this.snack.open('Evaluation failed to start.', 'Dismiss', { duration: 4000 });
        },
      });
  }

  get allUploaded(): boolean {
    return (
      this.status.student === 'done' &&
      this.status.exam === 'done' &&
      this.status.answers === 'done'
    );
  }
}
