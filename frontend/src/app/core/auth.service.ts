import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';

import { LoginResponse, Permission, User } from './models';

const STORAGE_KEY = 'hospital.session';

interface Session {
  token: string;
  expiresAt: string;
  user: User;
}

/**
 * Holds the logged-in session (JWT + user) and exposes it as signals.
 * The session is kept in localStorage so a page refresh doesn't log the user out.
 *
 * Note: hiding buttons based on permissions is only for convenience — the backend
 * enforces every permission on its own.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);

  private readonly session = signal<Session | null>(this.restore());

  readonly user = computed(() => this.session()?.user ?? null);
  readonly isAuthenticated = computed(() => this.session() !== null);
  readonly token = computed(() => this.session()?.token ?? null);

  login(username: string, password: string): Observable<LoginResponse> {
    return this.http.post<LoginResponse>('/api/auth/login', { username, password }).pipe(
      tap((res) => this.save({ token: res.access_token, expiresAt: res.expires_at, user: res.user })),
    );
  }

  logout(returnUrl?: string): void {
    this.session.set(null);
    try {
      localStorage.removeItem(STORAGE_KEY);
    } catch {
      /* storage unavailable */
    }
    this.router.navigate(['/login'], returnUrl ? { queryParams: { returnUrl } } : {});
  }

  hasPermission(permission: Permission): boolean {
    return this.user()?.permissions.includes(permission) ?? false;
  }

  private save(session: Session): void {
    this.session.set(session);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(session));
    } catch {
      /* storage unavailable — session lives in memory only */
    }
  }

  private restore(): Session | null {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return null;
      const session = JSON.parse(raw) as Session;
      return new Date(session.expiresAt) > new Date() ? session : null;
    } catch {
      return null;
    }
  }
}
