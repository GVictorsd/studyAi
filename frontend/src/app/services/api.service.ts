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

  evaluate(payload: EvaluateRequest): Observable<EvaluateResponse> {
    return this.http.post<EvaluateResponse>(`${this.base}/evaluate`, payload);
  }

  getReport(examId: string): Observable<ReportOut> {
    return this.http.get<ReportOut>(`${this.base}/report/${examId}`);
  }

  getStudyPlan(studentId: string): Observable<StudyPlanOut> {
    return this.http.get<StudyPlanOut>(`${this.base}/study-plan/${studentId}`);
  }
}
