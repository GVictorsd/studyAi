import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export interface CurrentStudent {
  id: string;
  name: string;
  email: string;
}

const STORAGE_KEY = 'studyai_student';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private _student$ = new BehaviorSubject<CurrentStudent | null>(this.load());

  get student$() {
    return this._student$.asObservable();
  }

  get student(): CurrentStudent | null {
    return this._student$.value;
  }

  get isLoggedIn(): boolean {
    return this._student$.value !== null;
  }

  login(student: CurrentStudent): void {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(student));
    this._student$.next(student);
  }

  logout(): void {
    localStorage.removeItem(STORAGE_KEY);
    this._student$.next(null);
  }

  private load(): CurrentStudent | null {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  }
}
