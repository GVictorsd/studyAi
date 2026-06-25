import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { UploadResponse, ExamUploadResponse } from '../models/api.models';

@Injectable({ providedIn: 'root' })
export class UploadService {
  private readonly base = environment.apiUrl;

  constructor(private http: HttpClient) {}

  uploadTextbook(file: File, title: string): Observable<UploadResponse> {
    const fd = new FormData();
    fd.append('file', file);
    fd.append('title', title);
    return this.http.post<UploadResponse>(`${this.base}/upload/textbook`, fd);
  }

  uploadExamPaper(
    studentId: string,
    textbookId?: string,
    file?: File,
    examText?: string
  ): Observable<ExamUploadResponse> {
    const fd = new FormData();
    fd.append('student_id', studentId);
    if (textbookId) fd.append('textbook_id', textbookId);
    if (file) fd.append('file', file);
    if (examText) fd.append('exam_text', examText);
    return this.http.post<ExamUploadResponse>(`${this.base}/upload/exam`, fd);
  }

  uploadAnswers(
    examId: string,
    file?: File,
    answerText?: string
  ): Observable<ExamUploadResponse> {
    const fd = new FormData();
    fd.append('exam_id', examId);
    if (file) fd.append('file', file);
    if (answerText) fd.append('answer_text', answerText);
    return this.http.post<ExamUploadResponse>(`${this.base}/upload/answers`, fd);
  }
}
