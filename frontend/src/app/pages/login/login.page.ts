import { ChangeDetectionStrategy, Component, inject, input, signal } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';

import { AuthService } from '../../core/auth.service';
import { describeError } from '../../core/http-error';

/** Seeded demo accounts (see backend/app/seed.py), shown as one-click shortcuts. */
const DEMO_USERS = [
  { username: 'dr_house', label: 'Doctor' },
  { username: 'nurse_joy', label: 'Nurse' },
  { username: 'pam_beesly', label: 'Secretary' },
];
const DEMO_PASSWORD = 'password123';

@Component({
  selector: 'app-login-page',
  imports: [ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="login-wrap">
      <form class="card login-card" [formGroup]="form" (ngSubmit)="submit()">
        <div class="login-head">
          <span class="brand-mark" aria-hidden="true">+</span>
          <h1>Ward Board</h1>
          <p class="muted">Hospital staff sign-in</p>
        </div>

        <label class="field">
          <span>Username</span>
          <input formControlName="username" autocomplete="username" />
        </label>

        <label class="field">
          <span>Password</span>
          <input type="password" formControlName="password" autocomplete="current-password" />
        </label>

        @if (error()) {
          <p class="alert alert-error" role="alert">{{ error() }}</p>
        }

        <button type="submit" class="btn btn-primary btn-block" [disabled]="form.invalid || submitting()">
          {{ submitting() ? 'Signing in…' : 'Sign in' }}
        </button>

        <div class="demo">
          <p class="muted small">Demo accounts (password: <code>{{ demoPassword }}</code>)</p>
          <div class="demo-buttons">
            @for (demo of demoUsers; track demo.username) {
              <button type="button" class="btn btn-outline btn-sm" (click)="fill(demo.username)">
                {{ demo.label }}
              </button>
            }
          </div>
        </div>
      </form>
    </div>
  `,
  styles: `
    .login-wrap {
      min-height: 100vh;
      display: grid;
      place-items: center;
      padding: 16px;
    }
    .login-card {
      width: 100%;
      max-width: 380px;
      display: flex;
      flex-direction: column;
      gap: 16px;
      padding: 32px;
    }
    .login-head {
      text-align: center;
    }
    .login-head h1 {
      margin: 12px 0 4px;
      font-size: 1.5rem;
    }
    .brand-mark {
      display: inline-grid;
      place-items: center;
      width: 44px;
      height: 44px;
      border-radius: 12px;
      background: var(--primary);
      color: white;
      font-size: 1.8rem;
      line-height: 1;
    }
    .demo {
      border-top: 1px solid var(--border);
      padding-top: 16px;
      text-align: center;
    }
    .demo-buttons {
      display: flex;
      gap: 8px;
      justify-content: center;
      flex-wrap: wrap;
    }
  `,
})
export class LoginPage {
  /** Where to go after logging in (set by the auth guard / interceptor). */
  readonly returnUrl = input<string>('/patients');

  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  protected readonly demoUsers = DEMO_USERS;
  protected readonly demoPassword = DEMO_PASSWORD;
  protected readonly submitting = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly form = inject(NonNullableFormBuilder).group({
    username: ['', Validators.required],
    password: ['', Validators.required],
  });

  fill(username: string): void {
    this.form.setValue({ username, password: DEMO_PASSWORD });
    this.error.set(null);
  }

  submit(): void {
    if (this.form.invalid) return;
    const { username, password } = this.form.getRawValue();
    this.submitting.set(true);
    this.error.set(null);

    this.auth.login(username, password).subscribe({
      next: () => this.router.navigateByUrl(this.returnUrl() || '/patients'),
      error: (err) => {
        this.error.set(describeError(err));
        this.submitting.set(false);
      },
    });
  }
}
