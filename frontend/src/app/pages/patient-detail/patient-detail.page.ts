import { DatePipe, DecimalPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject, input, signal } from '@angular/core';
import { takeUntilDestroyed, toObservable } from '@angular/core/rxjs-interop';
import { Router, RouterLink } from '@angular/router';
import { Observable, catchError, finalize, of, switchMap, tap } from 'rxjs';

import { HasPermissionDirective } from '../../core/has-permission.directive';
import { describeError } from '../../core/http-error';
import { Medication, MedicationCreate, PatientDetail, Vitals, VitalsCreate } from '../../core/models';
import { PatientApiService } from '../../core/patient-api.service';
import { PatientListStore } from '../../core/patient-list.store';
import { TimeAgoPipe } from '../../shared/time-ago.pipe';
import { DiagnosisFormComponent } from './diagnosis-form.component';
import { MedicationFormComponent } from './medication-form.component';
import { TimelineComponent } from './timeline.component';
import { VitalsFormComponent } from './vitals-form.component';

type Panel = 'vitals' | 'prescribe' | 'diagnosis';

/**
 * Patient page (/patients/:id): personal info, medical info, latest vitals, medications
 * and the timeline, plus the actions the current user's role allows.
 *
 * Loads from the fast single-patient endpoint, so it never waits for the slow list.
 * Each action returns the updated patient, which replaces the one on screen — no reload needed.
 */
@Component({
  selector: 'app-patient-detail-page',
  imports: [
    RouterLink,
    DatePipe,
    DecimalPipe,
    TimeAgoPipe,
    HasPermissionDirective,
    TimelineComponent,
    VitalsFormComponent,
    MedicationFormComponent,
    DiagnosisFormComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <a routerLink="/patients" class="back">← All patients</a>

    @if (loadError(); as error) {
      <div class="alert alert-error" role="alert">
        <span>{{ error }}</span>
        <a routerLink="/patients" class="btn btn-sm btn-outline">Back to list</a>
      </div>
    } @else if (patient(); as p) {
      <header class="head">
        <div>
          <h1>{{ p.full_name }}</h1>
          <p class="muted">
            ID <span class="mono">{{ p.id }}</span> · {{ p.ward_name }} · admitted
            {{ p.admitted_at | date: 'd MMM, HH:mm' }}
          </p>
        </div>
        <div class="head-actions">
          <a *appHasPermission="'update_patient_info'" [routerLink]="['/patients', p.id, 'edit']" class="btn btn-outline">
            Edit details
          </a>
          <button
            *appHasPermission="'delete_patient'"
            type="button"
            class="btn btn-danger"
            [disabled]="busy() !== null"
            (click)="deletePatient(p)"
          >
            {{ busy() === 'delete' ? 'Deleting…' : 'Delete' }}
          </button>
        </div>
      </header>

      @if (notice(); as message) {
        <p class="alert alert-success" role="status">{{ message }}</p>
      }
      @if (actionError(); as message) {
        <p class="alert alert-error" role="alert">{{ message }}</p>
      }

      <div class="layout">
        <div class="column">
          <!-- Personal details -->
          <section class="card">
            <h2>Personal details</h2>
            <dl class="facts">
              <div><dt>National ID</dt><dd class="mono">{{ p.id }}</dd></div>
              <div><dt>Sex</dt><dd>{{ p.sex === 'male' ? 'Male' : 'Female' }}</dd></div>
              <div>
                <dt>Age</dt>
                <dd>{{ p.age }} <span class="muted">({{ p.birth_date | date: 'd MMM y' }})</span></dd>
              </div>
              <div><dt>Health plan</dt><dd>{{ p.health_plan }}</dd></div>
              <div><dt>Ward</dt><dd>{{ p.ward_name }}</dd></div>
              <div><dt>Admitted</dt><dd>{{ p.admitted_at | date: 'd MMM y, HH:mm' }}</dd></div>
            </dl>
          </section>

          <!-- Diagnosis -->
          <section class="card">
            <div class="card-head">
              <h2>Diagnosis</h2>
              @if (panel() !== 'diagnosis') {
                <button *appHasPermission="'change_diagnosis'" type="button" class="btn btn-sm btn-outline"
                        (click)="openPanel('diagnosis')">
                  Change
                </button>
              }
            </div>
            @if (panel() === 'diagnosis') {
              <app-diagnosis-form
                [current]="p.diagnosis"
                [busy]="busy() === 'diagnosis'"
                (submitted)="changeDiagnosis($event)"
                (cancelled)="closePanel()"
              />
            } @else {
              <p class="diagnosis">{{ p.diagnosis }}</p>
            }
          </section>

          <!-- Vitals -->
          <section class="card">
            <div class="card-head">
              <h2>Latest vitals</h2>
              @if (panel() !== 'vitals') {
                <button *appHasPermission="'record_vitals'" type="button" class="btn btn-sm btn-outline"
                        (click)="openPanel('vitals')">
                  + Record vitals
                </button>
              }
            </div>
            @if (panel() === 'vitals') {
              <app-vitals-form [busy]="busy() === 'vitals'" (submitted)="recordVitals($event)" (cancelled)="closePanel()" />
            }
            @if (p.latest_vitals; as v) {
              <div class="vitals">
                <div class="vital" [class.abnormal]="isHeartRateAbnormal(v)">
                  <span class="vital-label">Heart rate</span>
                  <span class="vital-value">{{ v.heart_rate }}</span>
                  <span class="vital-unit">bpm</span>
                </div>
                <div class="vital" [class.abnormal]="isBloodPressureAbnormal(v)">
                  <span class="vital-label">Blood pressure</span>
                  <span class="vital-value">{{ v.bp_systolic }}/{{ v.bp_diastolic }}</span>
                  <span class="vital-unit">mmHg</span>
                </div>
                <div class="vital" [class.abnormal]="isTemperatureAbnormal(v)">
                  <span class="vital-label">Temperature</span>
                  <span class="vital-value">{{ v.temperature | number: '1.1-1' }}</span>
                  <span class="vital-unit">°C</span>
                </div>
              </div>
              <p class="muted small">
                Recorded {{ v.recorded_at | timeAgo }} by {{ v.recorded_by }} ·
                {{ v.recorded_at | date: 'd MMM, HH:mm' }}
              </p>
            } @else {
              <p class="muted">No vitals recorded yet.</p>
            }
          </section>

          <!-- Medications -->
          <section class="card">
            <div class="card-head">
              <h2>Medications</h2>
              @if (panel() !== 'prescribe') {
                <button *appHasPermission="'prescribe_medication'" type="button" class="btn btn-sm btn-outline"
                        (click)="openPanel('prescribe')">
                  + Prescribe
                </button>
              }
            </div>
            @if (panel() === 'prescribe') {
              <app-medication-form [busy]="busy() === 'prescribe'" (submitted)="prescribe($event)" (cancelled)="closePanel()" />
            }
            <ul class="meds">
              @for (m of p.medications; track m.id) {
                <li class="med" [class.inactive]="!m.active">
                  <div>
                    <div class="med-name">{{ m.name }} <span class="muted">{{ m.dose }}</span></div>
                    <div class="muted small">{{ m.frequency }} · prescribed by {{ m.prescribed_by }}</div>
                    <div class="small">
                      @if (m.last_given_at) {
                        Last given {{ m.last_given_at | timeAgo }} by {{ m.last_given_by }}
                      } @else {
                        <span class="not-given">Not given yet</span>
                      }
                    </div>
                  </div>
                  @if (m.active) {
                    <button *appHasPermission="'give_medication'" type="button" class="btn btn-sm btn-primary"
                            [disabled]="busy() !== null" (click)="giveMedication(m)">
                      {{ busy() === 'give:' + m.id ? 'Saving…' : 'Mark as given' }}
                    </button>
                  } @else {
                    <span class="tag">Stopped</span>
                  }
                </li>
              } @empty {
                <li class="muted">No medications.</li>
              }
            </ul>
          </section>
        </div>

        <div class="column">
          <app-timeline [events]="p.timeline" />
        </div>
      </div>
    } @else {
      <!-- First load -->
      <div class="card" aria-hidden="true">
        <div class="skeleton" style="height: 26px; width: 260px"></div>
        <div class="skeleton" style="height: 14px; width: 340px; margin-top: 12px"></div>
      </div>
    }
  `,
  styles: `
    .back {
      display: inline-block;
      margin-bottom: 12px;
      text-decoration: none;
      font-weight: 500;
    }
    .head {
      display: flex;
      flex-wrap: wrap;
      align-items: flex-end;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 16px;
    }
    .head h1 { margin: 0; }
    .head p { margin: 4px 0 0; }
    .head-actions { display: flex; gap: 8px; }
    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 20px;
      align-items: start;
    }
    .column { display: flex; flex-direction: column; gap: 20px; min-width: 0; }
    h2 { margin: 0 0 12px; font-size: 1.05rem; }
    .card-head h2 { margin: 0; }
    .facts {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px 20px;
      margin: 0;
    }
    .facts dt { font-size: 0.8rem; color: var(--muted); }
    .facts dd { margin: 2px 0 0; font-weight: 500; }
    .diagnosis { margin: 0; font-size: 1.05rem; font-weight: 500; }
    .vitals {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
      margin-bottom: 8px;
    }
    .vital {
      display: flex;
      flex-direction: column;
      padding: 12px;
      border-radius: 10px;
      background: var(--surface-2);
      border: 1px solid var(--border);
    }
    .vital.abnormal { border-color: var(--warning); }
    .vital.abnormal .vital-value { color: var(--warning); }
    .vital-label { font-size: 0.8rem; color: var(--muted); }
    .vital-value { font-size: 1.5rem; font-weight: 700; font-variant-numeric: tabular-nums; }
    .vital-unit { font-size: 0.75rem; color: var(--muted); }
    .meds { list-style: none; margin: 0; padding: 0; }
    .med {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 12px 0;
      border-top: 1px solid var(--border);
    }
    .med:first-child { border-top: none; }
    .med.inactive { opacity: 0.6; }
    .med-name { font-weight: 600; }
    .not-given { color: var(--warning); font-weight: 500; }
    .tag {
      padding: 2px 8px;
      border-radius: 6px;
      background: var(--surface-2);
      color: var(--muted);
      font-size: 0.8rem;
    }
    @media (max-width: 900px) {
      .layout { grid-template-columns: minmax(0, 1fr); }
    }
    @media (max-width: 500px) {
      .vitals, .facts { grid-template-columns: minmax(0, 1fr); }
    }
  `,
})
export class PatientDetailPage {
  /** From the route parameter :id (router input binding). */
  readonly id = input.required<string>();

  private readonly api = inject(PatientApiService);
  private readonly listStore = inject(PatientListStore);
  private readonly router = inject(Router);

  protected readonly patient = signal<PatientDetail | null>(null);
  protected readonly loadError = signal<string | null>(null);
  /** Which action is in progress (e.g. 'vitals', 'give:<medication id>'), or null. */
  protected readonly busy = signal<string | null>(null);
  protected readonly panel = signal<Panel | null>(null);
  protected readonly notice = signal<string | null>(null);
  protected readonly actionError = signal<string | null>(null);

  constructor() {
    // Reload whenever the :id changes. switchMap cancels the previous request, and
    // takeUntilDestroyed cancels an in-flight request when the user leaves the page.
    toObservable(this.id)
      .pipe(
        tap(() => {
          this.patient.set(null);
          this.loadError.set(null);
          this.panel.set(null);
        }),
        switchMap((id) =>
          this.api.get(id).pipe(
            catchError((err: unknown) => {
              this.loadError.set(describeError(err));
              return of(null);
            }),
          ),
        ),
        takeUntilDestroyed(),
      )
      .subscribe((patient) => this.patient.set(patient));
  }

  protected openPanel(panel: Panel): void {
    this.panel.set(panel);
    this.notice.set(null);
    this.actionError.set(null);
  }

  protected closePanel(): void {
    this.panel.set(null);
  }

  protected changeDiagnosis(diagnosis: string): void {
    this.run('diagnosis', this.api.changeDiagnosis(this.id(), diagnosis), 'Diagnosis updated.');
  }

  protected prescribe(medication: MedicationCreate): void {
    this.run('prescribe', this.api.prescribe(this.id(), medication), `${medication.name} prescribed.`);
  }

  protected recordVitals(vitals: VitalsCreate): void {
    this.run('vitals', this.api.recordVitals(this.id(), vitals), 'Vitals recorded.');
  }

  protected giveMedication(medication: Medication): void {
    this.run(
      `give:${medication.id}`,
      this.api.giveMedication(this.id(), medication.id),
      `${medication.name} marked as given.`,
    );
  }

  protected deletePatient(patient: PatientDetail): void {
    if (!confirm(`Delete ${patient.full_name} (${patient.id})? This cannot be undone.`)) return;

    this.busy.set('delete');
    this.actionError.set(null);
    this.api
      .delete(patient.id)
      .pipe(finalize(() => this.busy.set(null)))
      .subscribe({
        next: () => {
          this.listStore.forget(patient.id);
          this.router.navigate(['/patients']);
        },
        error: (err: unknown) => this.actionError.set(describeError(err)),
      });
  }

  protected isHeartRateAbnormal(v: Vitals): boolean {
    return v.heart_rate < 50 || v.heart_rate > 100;
  }

  protected isBloodPressureAbnormal(v: Vitals): boolean {
    return v.bp_systolic >= 140 || v.bp_diastolic >= 90 || v.bp_systolic < 90;
  }

  protected isTemperatureAbnormal(v: Vitals): boolean {
    return v.temperature >= 38 || v.temperature < 35;
  }

  /** Run an action: show progress, replace the patient with the server's response, report errors. */
  private run(action: string, request: Observable<PatientDetail>, successMessage: string): void {
    this.busy.set(action);
    this.notice.set(null);
    this.actionError.set(null);

    request.pipe(finalize(() => this.busy.set(null))).subscribe({
      next: (patient) => {
        this.patient.set(patient);
        this.panel.set(null);
        this.notice.set(successMessage);
      },
      error: (err: unknown) => this.actionError.set(describeError(err)),
    });
  }
}
