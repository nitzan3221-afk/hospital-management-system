import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { Router, RouterLink } from '@angular/router';

import { HasPermissionDirective } from '../../core/has-permission.directive';
import { PatientSummary, WardGroup } from '../../core/models';
import { PatientListStore } from '../../core/patient-list.store';
import { TimeAgoPipe } from '../../shared/time-ago.pipe';

/**
 * Main page: all patients grouped by ward.
 * Backed by the deliberately slow endpoint — see PatientListStore for how that is handled.
 */
@Component({
  selector: 'app-patient-list-page',
  imports: [RouterLink, DatePipe, TimeAgoPipe, HasPermissionDirective],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="page-head">
      <div>
        <h1>Patients</h1>
        <p class="muted">
          @if (store.hasData()) {
            {{ store.totalPatients() }} patients in {{ store.groups()!.length }} wards
            @if (store.lastUpdated(); as updated) {
              · updated {{ updated | date: 'HH:mm:ss' }}
            }
          } @else {
            Overview of all wards
          }
        </p>
      </div>

      <div class="head-actions">
        <input class="search" type="search" placeholder="Search name, ID or diagnosis"
               [value]="query()" (input)="query.set($any($event.target).value)" aria-label="Search patients" />
        <button type="button" class="btn btn-outline" (click)="store.load()" [disabled]="store.loading()">
          {{ store.loading() ? 'Refreshing…' : 'Refresh' }}
        </button>
        <a *appHasPermission="'create_patient'" routerLink="/patients/new" class="btn btn-primary">+ Add patient</a>
      </div>
    </div>

    <!-- Loading feedback: a thin progress bar always, a notice once it is clearly slow -->
    @if (store.loading()) {
      <div class="progress" role="progressbar" aria-label="Loading patients"><span></span></div>
      @if (store.isSlow()) {
        <p class="alert alert-info" role="status">
          @if (store.hasData()) {
            Showing the last loaded list while fetching a fresh one ({{ store.elapsedSeconds() }}s)…
          } @else {
            Still loading — the ward overview is a heavy query and can take a few seconds
            ({{ store.elapsedSeconds() }}s)…
          }
        </p>
      }
    }

    @if (store.error(); as error) {
      <div class="alert alert-error" role="alert">
        <span>Could not load the patient list: {{ error }}</span>
        <button type="button" class="btn btn-sm btn-outline" (click)="store.load()">Retry</button>
      </div>
    }

    @if (filteredGroups(); as groups) {
      @for (group of groups; track group.ward) {
        <section class="ward card">
          <header class="ward-head">
            <h2>{{ group.ward_name }}</h2>
            <span class="count">{{ group.patients.length }}</span>
          </header>

          <div class="table-wrap">
            <table class="patients">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>ID</th>
                  <th>Age / Sex</th>
                  <th>Diagnosis</th>
                  <th>Last vitals</th>
                  <th class="num">Active meds</th>
                </tr>
              </thead>
              <tbody>
                @for (patient of group.patients; track patient.id) {
                  <tr tabindex="0" (click)="open(patient)" (keydown.enter)="open(patient)">
                    <td class="strong">{{ patient.full_name }}</td>
                    <td class="mono">{{ patient.id }}</td>
                    <td>{{ patient.age }} · {{ patient.sex === 'male' ? 'M' : 'F' }}</td>
                    <td>{{ patient.diagnosis }}</td>
                    <td [class.stale]="isVitalsStale(patient)" [title]="patient.last_vitals_at | date: 'medium'">
                      {{ patient.last_vitals_at | timeAgo }}
                    </td>
                    <td class="num">{{ patient.active_medications }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </section>
      } @empty {
        <p class="empty card">
          {{ query() ? 'No patients match "' + query() + '".' : 'No patients are currently admitted.' }}
        </p>
      }
    } @else if (store.loading()) {
      <!-- First load: skeleton placeholders shaped like the real content -->
      @for (ward of skeletonWards; track ward) {
        <section class="ward card" aria-hidden="true">
          <div class="skeleton skeleton-title"></div>
          @for (row of skeletonRows; track row) {
            <div class="skeleton skeleton-row"></div>
          }
        </section>
      }
    }
  `,
  styles: `
    .page-head {
      display: flex;
      flex-wrap: wrap;
      align-items: flex-end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 16px;
    }
    .page-head h1 { margin: 0; }
    .page-head p { margin: 4px 0 0; }
    .head-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      align-items: center;
    }
    .search { min-width: 240px; }
    .ward { margin-bottom: 20px; padding: 0; overflow: hidden; }
    .ward-head {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 14px 20px;
      border-bottom: 1px solid var(--border);
    }
    .ward-head h2 { margin: 0; font-size: 1.05rem; }
    .count {
      padding: 2px 9px;
      border-radius: 999px;
      background: var(--primary-soft);
      color: var(--primary);
      font-size: 0.8rem;
      font-weight: 600;
    }
    .table-wrap { overflow-x: auto; }
    .patients { width: 100%; border-collapse: collapse; }
    .patients th {
      text-align: left;
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--muted);
      padding: 10px 20px;
      background: var(--surface-2);
    }
    .patients td {
      padding: 12px 20px;
      border-top: 1px solid var(--border);
      white-space: nowrap;
    }
    .patients td:nth-child(4) { white-space: normal; min-width: 200px; }
    .patients tbody tr { cursor: pointer; }
    .patients tbody tr:hover, .patients tbody tr:focus-visible { background: var(--primary-soft); outline: none; }
    .num { text-align: right; }
    .strong { font-weight: 600; }
    .stale { color: var(--warning); font-weight: 600; }
    .empty { padding: 32px; text-align: center; color: var(--muted); }
    .progress {
      position: relative;
      height: 3px;
      margin-bottom: 12px;
      overflow: hidden;
      border-radius: 3px;
      background: var(--primary-soft);
    }
    .progress span {
      position: absolute;
      inset: 0 auto 0 0;
      width: 35%;
      background: var(--primary);
      animation: slide 1.1s ease-in-out infinite;
    }
    @keyframes slide {
      from { left: -35%; }
      to { left: 100%; }
    }
    .skeleton-title { height: 18px; width: 180px; margin: 18px 20px; }
    .skeleton-row { height: 14px; margin: 16px 20px; }
    @media (max-width: 600px) {
      .search { min-width: 0; flex: 1; }
    }
  `,
})
export class PatientListPage implements OnInit {
  protected readonly store = inject(PatientListStore);
  private readonly router = inject(Router);

  protected readonly query = signal('');
  protected readonly skeletonWards = [1, 2, 3];
  protected readonly skeletonRows = [1, 2, 3, 4];

  /** Client-side filter over the (cached) list — instant, no extra slow request. */
  protected readonly filteredGroups = computed<WardGroup[] | null>(() => {
    const groups = this.store.groups();
    const q = this.query().trim().toLowerCase();
    if (!groups || !q) return groups;
    return groups
      .map((g) => ({
        ...g,
        patients: g.patients.filter((p) =>
          [p.full_name, p.id, p.diagnosis].some((field) => field.toLowerCase().includes(q)),
        ),
      }))
      .filter((g) => g.patients.length > 0);
  });

  ngOnInit(): void {
    this.store.load();
  }

  open(patient: PatientSummary): void {
    this.router.navigate(['/patients', patient.id]);
  }

  /** Highlight patients whose vitals are older than 8 hours (or missing). */
  isVitalsStale(patient: PatientSummary): boolean {
    if (!patient.last_vitals_at) return true;
    return Date.now() - new Date(patient.last_vitals_at).getTime() > 8 * 60 * 60 * 1000;
  }
}
