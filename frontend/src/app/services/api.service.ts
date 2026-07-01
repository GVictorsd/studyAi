import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  StudentCreate,
  StudentOut,
  EvaluateRequest,
  EvaluateResponse,
  ReportOut,
  StudyPlanOut,
  ExamListItem,
  TextbookOut,
  InsightsOut,
} from '../models/api.models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly base = environment.apiUrl;

  constructor(private http: HttpClient) {}

  createStudent(payload: StudentCreate): Observable<StudentOut> {
    return this.http.post<StudentOut>(`${this.base}/students`, payload);
  }

  getStudent(studentId: string): Observable<StudentOut> {
    return this.http.get<StudentOut>(`${this.base}/students/${studentId}`);
  }

  getTextbooks(): Observable<TextbookOut[]> {
    return this.http.get<TextbookOut[]>(`${this.base}/textbooks`);
  }

  getStudentByEmail(email: string): Observable<StudentOut> {
    return this.http.get<StudentOut>(`${this.base}/students/by-email/${encodeURIComponent(email)}`);
  }

  getStudentExams(studentId: string): Observable<ExamListItem[]> {
    return this.http.get<ExamListItem[]>(`${this.base}/students/${studentId}/exams`);
  }

  evaluate(payload: EvaluateRequest): Observable<EvaluateResponse> {
    return this.http.post<EvaluateResponse>(`${this.base}/evaluate`, payload);
  }

  getReport(examId: string): Observable<ReportOut> {
    return this.http.get<ReportOut>(`${this.base}/report/${examId}`);
  }

  getStudyPlan(studentId: string): Observable<StudyPlanOut> {
    return this.http.get<StudyPlanOut>(`${this.base}/study-plan/${studentId}`);
  }

  getGlobalStudyPlan(studentId: string): Observable<StudyPlanOut> {
    return this.http.get<StudyPlanOut>(`${this.base}/study-plan/${studentId}/global`);
  }

  refreshGlobalStudyPlan(studentId: string): Observable<StudyPlanOut> {
    return this.http.post<StudyPlanOut>(`${this.base}/study-plan/${studentId}/refresh`, {});
  }

  getInsights(studentId: string): Observable<InsightsOut> {
    return this.http.get<InsightsOut>(`${this.base}/insights/${studentId}`);
  }

  refreshInsights(studentId: string): Observable<InsightsOut> {
    return this.http.post<InsightsOut>(`${this.base}/insights/${studentId}/refresh`, {});
  }
}
