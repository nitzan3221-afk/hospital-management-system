import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { AbstractControl, FormControl, FormGroup, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';

import { VitalsCreate } from '../../core/models';

/** Same ranges as the backend (app/domain/models.py) so most mistakes are caught before sending. */
const LIMITS = {
  heart_rate: { label: 'Heart rate', unit: 'bpm', min: 20, max: 250, step: 1 },
  bp_systolic: { label: 'Systolic', unit: 'mmHg', min: 50, max: 260, step: 1 },
  bp_diastolic: { label: 'Diastolic', unit: 'mmHg', min: 30, max: 160, step: 1 },
  temperature: { label: 'Temperature', unit: '°C', min: 30, max: 45, step: 0.1 },
} as const;

type VitalKey = keyof typeof LIMITS;

function vitalControl(key: VitalKey): FormControl<number | null> {
  const { min, max } = LIMITS[key];
  return new FormControl<number | null>(null, [Validators.required, Validators.min(min), Validators.max(max)]);
}

function systolicAboveDiastolic(group: AbstractControl): ValidationErrors | null {
  const systolic = group.get('bp_systolic')?.value;
  const diastolic = group.get('bp_diastolic')?.value;
  return systolic != null && diastolic != null && systolic <= diastolic ? { bpOrder: true } : null;
}

/** Form for recording a set of vital signs. Emits the values; the parent page calls the API. */
@Component({
  selector: 'app-vitals-form',
  imports: [ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <form class="inline-form" [formGroup]="form" (ngSubmit)="submit()">
      <div class="form-grid">
        @for (key of keys; track key) {
          <label class="field">
            <span>{{ limits[key].label }} ({{ limits[key].unit }})</span>
            <input
              type="number"
              [formControlName]="key"
              [min]="limits[key].min"
              [max]="limits[key].max"
              [step]="limits[key].step"
            />
          </label>
        }
      </div>

      @if (errorMessage(); as message) {
        <p class="field-error">{{ message }}</p>
      }

      <div class="form-actions">
        <button type="button" class="btn btn-ghost" (click)="cancelled.emit()">Cancel</button>
        <button type="submit" class="btn btn-primary" [disabled]="busy()">
          {{ busy() ? 'Saving…' : 'Save vitals' }}
        </button>
      </div>
    </form>
  `,
})
export class VitalsFormComponent {
  readonly busy = input(false);
  readonly submitted = output<VitalsCreate>();
  readonly cancelled = output<void>();

  protected readonly limits = LIMITS;
  protected readonly keys = Object.keys(LIMITS) as VitalKey[];

  protected readonly form = new FormGroup(
    {
      heart_rate: vitalControl('heart_rate'),
      bp_systolic: vitalControl('bp_systolic'),
      bp_diastolic: vitalControl('bp_diastolic'),
      temperature: vitalControl('temperature'),
    },
    { validators: systolicAboveDiastolic },
  );

  protected errorMessage(): string | null {
    for (const key of this.keys) {
      const control = this.form.controls[key];
      if (control.touched && control.invalid) {
        const { label, min, max } = LIMITS[key];
        return `${label}: enter a value between ${min} and ${max}.`;
      }
    }
    if (this.form.touched && this.form.hasError('bpOrder')) {
      return 'Systolic pressure must be higher than diastolic.';
    }
    return null;
  }

  protected submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.submitted.emit(this.form.getRawValue() as VitalsCreate);
  }
}
