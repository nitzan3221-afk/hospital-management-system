import { ChangeDetectionStrategy, Component, inject, input, output } from '@angular/core';
import { NonNullableFormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';

import { MedicationCreate } from '../../core/models';

/** Form for prescribing a new medication. Emits the values; the parent page calls the API. */
@Component({
  selector: 'app-medication-form',
  imports: [ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <form class="inline-form" [formGroup]="form" (ngSubmit)="submit()">
      <div class="form-grid">
        <label class="field">
          <span>Medication</span>
          <input formControlName="name" placeholder="e.g. Amoxicillin" />
        </label>
        <label class="field">
          <span>Dose</span>
          <input formControlName="dose" placeholder="e.g. 500 mg" />
        </label>
        <label class="field">
          <span>Frequency</span>
          <input formControlName="frequency" placeholder="e.g. every 8 hours" />
        </label>
      </div>

      @if (form.touched && form.invalid) {
        <p class="field-error">All three fields are required.</p>
      }

      <div class="form-actions">
        <button type="button" class="btn btn-ghost" (click)="cancelled.emit()">Cancel</button>
        <button type="submit" class="btn btn-primary" [disabled]="busy()">
          {{ busy() ? 'Saving…' : 'Prescribe' }}
        </button>
      </div>
    </form>
  `,
})
export class MedicationFormComponent {
  readonly busy = input(false);
  readonly submitted = output<MedicationCreate>();
  readonly cancelled = output<void>();

  protected readonly form = inject(NonNullableFormBuilder).group({
    name: ['', [Validators.required, Validators.maxLength(100)]],
    dose: ['', [Validators.required, Validators.maxLength(50)]],
    frequency: ['', [Validators.required, Validators.maxLength(50)]],
  });

  protected submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const { name, dose, frequency } = this.form.getRawValue();
    this.submitted.emit({ name: name.trim(), dose: dose.trim(), frequency: frequency.trim() });
  }
}
