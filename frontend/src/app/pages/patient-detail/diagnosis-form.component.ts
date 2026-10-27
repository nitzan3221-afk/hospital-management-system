import { ChangeDetectionStrategy, Component, OnInit, input, output, signal } from '@angular/core';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';

/** Form for changing the diagnosis. Emits the new text; the parent page calls the API. */
@Component({
  selector: 'app-diagnosis-form',
  imports: [ReactiveFormsModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <form class="inline-form" [formGroup]="form" (ngSubmit)="submit()">
      <label class="field">
        <span>New diagnosis</span>
        <input formControlName="diagnosis" />
      </label>

      @if (error()) {
        <p class="field-error">{{ error() }}</p>
      }

      <div class="form-actions">
        <button type="button" class="btn btn-ghost" (click)="cancelled.emit()">Cancel</button>
        <button type="submit" class="btn btn-primary" [disabled]="busy()">
          {{ busy() ? 'Saving…' : 'Save diagnosis' }}
        </button>
      </div>
    </form>
  `,
})
export class DiagnosisFormComponent implements OnInit {
  readonly current = input.required<string>();
  readonly busy = input(false);
  readonly submitted = output<string>();
  readonly cancelled = output<void>();

  protected readonly form = new FormGroup({
    diagnosis: new FormControl('', {
      nonNullable: true,
      validators: [Validators.required, Validators.maxLength(200)],
    }),
  });
  protected readonly error = signal<string | null>(null);

  ngOnInit(): void {
    this.form.controls.diagnosis.setValue(this.current());
  }

  protected submit(): void {
    const control = this.form.controls.diagnosis;
    const value = control.value.trim();
    if (!value || control.invalid) {
      this.error.set('Enter a diagnosis (up to 200 characters).');
    } else if (value === this.current()) {
      this.error.set('This is already the current diagnosis.');
    } else {
      this.error.set(null);
      this.submitted.emit(value);
    }
  }
}
