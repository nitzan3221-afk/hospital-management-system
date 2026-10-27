import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';

import { AuthService } from '../core/auth.service';
import { ROLE_LABELS } from '../core/models';
import { PatientListStore } from '../core/patient-list.store';

/** App frame for logged-in users: top bar with the current user and a logout button. */
@Component({
  selector: 'app-shell',
  imports: [RouterOutlet, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header class="topbar">
      <a routerLink="/patients" class="brand">
        <span class="brand-mark" aria-hidden="true">+</span>
        <span>Ward Board</span>
      </a>

      @if (auth.user(); as user) {
        <div class="user">
          <span class="user-name">{{ user.full_name }}</span>
          <span class="role-badge role-{{ user.role }}">{{ roleLabels[user.role] }}</span>
          <button type="button" class="btn btn-ghost" (click)="logout()">Log out</button>
        </div>
      }
    </header>

    <main class="page">
      <router-outlet />
    </main>
  `,
  styles: `
    .topbar {
      position: sticky;
      top: 0;
      z-index: 10;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
      padding: 12px 24px;
      background: var(--surface);
      border-bottom: 1px solid var(--border);
    }
    .brand {
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 700;
      font-size: 1.1rem;
      color: var(--text);
      text-decoration: none;
    }
    .brand-mark {
      display: grid;
      place-items: center;
      width: 28px;
      height: 28px;
      border-radius: 8px;
      background: var(--primary);
      color: white;
      font-size: 1.2rem;
      line-height: 1;
    }
    .user {
      display: flex;
      align-items: center;
      gap: 12px;
    }
    .user-name {
      font-weight: 500;
    }
    @media (max-width: 600px) {
      .topbar { padding: 10px 16px; }
      .user-name { display: none; }
    }
  `,
})
export class ShellComponent {
  protected readonly auth = inject(AuthService);
  protected readonly roleLabels = ROLE_LABELS;
  private readonly listStore = inject(PatientListStore);

  logout(): void {
    this.listStore.reset();
    this.auth.logout();
  }
}
