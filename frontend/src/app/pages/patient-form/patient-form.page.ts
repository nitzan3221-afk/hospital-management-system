import { ChangeDetectionStrategy, Component, OnInit, computed, inject, input, signal } from '@angular/core';
import { AbstractControl, NonNullableFormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { Observable, finalize } from 'rxjs';

import { describeError } from '../../core/http-error';
import {
  HEALTH_PLANS,
  HealthPlan,
  PatientCreate,
  PatientDetail,
  PatientInfo,
  Sex,
  WARDS,
  Ward,
} from '../../core/models';
import { PatientApiService } from '../../core/patient-api.service';

type FieldName = keyof PatientCreate;

/** Fields the secretary may change on an existing patient (ID and diagnosis are not among them). */
const INFO_FIELDS: (keyof PatientInfo)[] = ['first_name', 'last_name', 'sex', 'birth_date', 'health_plan', 'ward'];

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function notInFuture(control: AbstractControl): ValidationErrors | null {
  return control.value && control.value > todayIso() ? { future: true } : null;
}

/**
 * One page for both "Add patient" (/patients/new) and "Edit details" (/patients/:id/edit).
 * In edit mode the national ID and diagnosis are read-only, and only changed fields are sent.
 */
@Component({
  selector: 'app-patient-form-page',
  imports: [ReactiveFormsModule, RouterLink],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <a [routerLink]="backLink()" class="back">← Back</a>
    <h1>{{ isEdit() ? 'Edit ' + (patientName() || 'patient') : 'Add patient' }}</h1>
    @if (isEdit()) {
      <p class="muted">The diagnosis is changed by a doctor from the patient page.</p>
    }

    @if (error(); as message) {
      <p class="alert alert-error" role="alert">{{ message }}</p>
    }
    @if (loading()) {
      <p class="muted">Loading patient…</p>
    }

    <form class="card" [formGroup]="form" (ngSubmit)="submit()">
      <div class="form-grid">
        <label class="field">
          <span>National ID</span>
          <input formControlName="id" inputmode="numeric" maxlength="9" placeholder="9 digits" />
          @if (showError('id')) {
            <small class="field-error">Must be exactly 9 digits.</small>
          }
        </label>

        <label class="field">
          <span>Ward</span>
          <select formControlName="ward">
            <option value="" disabled>Select ward…</option>
            @for (ward of wards; track ward.value) {
              <option [value]="ward.value">{{ ward.label }}</option>
            }
          </select>
          @if (showError('ward')) {
            <small class="field-error">Choose a ward.</small>
          }
        </label>

        <label class="field">
          <span>First name</span>
          <input formControlName="first_name" autocomplete="off" />
          @if (showError('first_name')) {
            <small class="field-error">Required (up to 50 characters).</small>
          }
        </label>

        <label class="field">
          <span>Last name</span>
          <input formControlName="last_name" autocomplete="off" />
          @if (showError('last_name')) {
            <small class="field-error">Required (up to 50 characters).</small>
          }
        </label>

        <label class="field">
          <span>Sex</span>
          <select formControlName="sex">
            <option value="" disabled>Select…</option>
            <option value="female">Female</option>
            <option value="male">Male</option>
          </select>
          @if (showError('sex')) {
            <small class="field-error">Required.</small>
          }
        </label>

        <label class="field">
          <span>Date of birth</span>
          <input type="date" formControlName="birth_date" [max]="today" />
          @if (showError('birth_date')) {
            <small class="field-error">Required, and not in the future.</small>
          }
        </label>

        <label class="field">
          <span>Health plan</span>
          <select formControlName="health_plan">
            <option value="" disabled>Select…</option>
            @for (plan of healthPlans; track plan) {
              <option [value]="plan">{{ plan }}</option>
            }
          </select>
          @if (showError('health_plan')) {
            <small class="field-error">Required.</small>
          }
        </label>

        <label class="field full">
          <span>{{ isEdit() ? 'Diagnosis (read-only)' : 'Initial diagnosis' }}</span>
          <input formControlName="diagnosis" autocomplete="off" />
          @if (showError('diagnosis')) {
            <small class="field-error">Required (up to 200 characters).</small>
          }
        </label>
      </div>

      <div class="form-actions">
        <a [routerLink]="backLink()" class="btn btn-ghost">Cancel</a>
        <button type="submit" class="btn btn-primary" [disabled]="saving() || loading()">
          {{ saving() ? 'Saving…' : isEdit() ? 'Save changes' : 'Add patient' }}
        </button>
      </div>
    </form>
  `,
  styles: `
    .back {
      display: inline-block;
      margin-bottom: 12px;
      text-decoration: none;
      font-weight: 500;
    }
    h1 { margin: 0 0 4px; }
    form { max-width: 760px; margin-top: 16px; }
    .full { grid-column: 1 / -1; }
  `,
})
export class PatientFormPage implements OnInit {
  /** Route parameter :id — present when editing, absent when adding. */
  readonly id = input<string>();

  private readonly api = inject(PatientApiService);
  private readonly router = inject(Router);

  protected readonly wards = WARDS;
  protected readonly healthPlans = HEALTH_PLANS;
  protected readonly today = todayIso();

  protected readonly isEdit = computed(() => !!this.id());
  protected readonly backLink = computed(() => (this.id() ? ['/patients', this.id()] : ['/patients']));
  protected readonly loading = signal(false);
  protected readonly saving = signal(false);
  protected readonly error = signal<string | null>(null);
  protected readonly patientName = signal('');

  protected readonly form = inject(NonNullableFormBuilder).group({
    id: ['', [Validators.required, Validators.pattern(/^\d{9}$/)]],
    first_name: ['', [Validators.required, Validators.maxLength(50)]],
    last_name: ['', [Validators.required, Validators.maxLength(50)]],
    sex: ['' as Sex | '', Validators.required],
    birth_date: ['', [Validators.required, notInFuture]],
    health_plan: ['' as HealthPlan | '', Validators.required],
    ward: ['' as Ward | '', Validators.required],
    diagnosis: ['', [Validators.required, Validators.maxLength(200)]],
  });

  ngOnInit(): void {
    const id = this.id();
    if (!id) return; // add mode

    this.form.controls.id.disable();
    this.form.controls.diagnosis.disable();
    this.loading.set(true);
    this.api
      .get(id)
      .pipe(finalize(() => this.loading.set(false)))
      .subscribe({
        next: (patient) => {
          this.patientName.set(patient.full_name);
          this.form.patchValue({
            id: patient.id,
            first_name: patient.first_name,
            last_name: patient.last_name,
            sex: patient.sex,
            birth_date: patient.birth_date,
            health_plan: patient.health_plan,
            ward: patient.ward,
            diagnosis: patient.diagnosis,
          });
        },
        error: (err: unknown) => this.error.set(describeError(err)),
      });
  }

  protected showError(name: FieldName): boolean {
    const control = this.form.controls[name];
    return control.invalid && control.touched;
  }

  protected submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const id = this.id();
    const request = id ? this.buildUpdate(id) : this.api.create(this.form.getRawValue() as PatientCreate);
    if (!request) {
      this.error.set('Nothing to save: no field was changed.');
      return;
    }

    this.saving.set(true);
    this.error.set(null);
    request.pipe(finalize(() => this.saving.set(false))).subscribe({
      next: (patient) => this.router.navigate(['/patients', patient.id]),
      error: (err: unknown) => this.error.set(describeError(err)),
    });
  }

  /** PATCH only the fields the user actually changed. */
  private buildUpdate(id: string): Observable<PatientDetail> | null {
    const values = this.form.getRawValue();
    const changes: Record<string, string> = {};
    for (const field of INFO_FIELDS) {
      if (this.form.controls[field].dirty) {
        changes[field] = values[field];
      }
    }
    return Object.keys(changes).length ? this.api.update(id, changes as Partial<PatientInfo>) : null;
  }
}
