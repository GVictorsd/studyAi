import { Component } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ApiService } from '../../services/api.service';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
})
export class LoginComponent {
  emailForm: FormGroup;
  nameForm: FormGroup;

  /** 'email' = step 1 (enter email), 'name' = step 2 (new user, enter name) */
  step: 'email' | 'name' = 'email';
  loading = false;

  private pendingEmail = '';

  constructor(
    private fb: FormBuilder,
    private api: ApiService,
    private auth: AuthService,
    private router: Router,
    private snack: MatSnackBar
  ) {
    this.emailForm = this.fb.group({
      email: ['', [Validators.required, Validators.email]],
    });
    this.nameForm = this.fb.group({
      name: ['', [Validators.required, Validators.minLength(2)]],
    });
  }

  checkEmail(): void {
    if (this.emailForm.invalid) return;
    this.loading = true;
    const { email } = this.emailForm.value;

    this.api.getStudentByEmail(email).subscribe({
      next: (student) => {
        this.auth.login({ id: student.id, name: student.name, email: student.email });
        this.loading = false;
        this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        this.loading = false;
        if (err.status === 404) {
          this.pendingEmail = email;
          this.step = 'name';
        } else {
          this.snack.open('Something went wrong. Please try again.', 'Dismiss', { duration: 4000 });
        }
      },
    });
  }

  register(): void {
    if (this.nameForm.invalid) return;
    this.loading = true;
    const { name } = this.nameForm.value;

    this.api.createStudent({ name, email: this.pendingEmail }).subscribe({
      next: (student) => {
        this.auth.login({ id: student.id, name: student.name, email: student.email });
        this.loading = false;
        this.router.navigate(['/dashboard']);
      },
      error: (e) => {
        this.loading = false;
        this.snack.open(e.error?.detail ?? 'Failed to create account.', 'Dismiss', { duration: 4000 });
      },
    });
  }

  backToEmail(): void {
    this.step = 'email';
    this.nameForm.reset();
  }
}
