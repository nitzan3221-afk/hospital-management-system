import { Injectable, computed, inject, signal } from '@angular/core';
import { Subscription, finalize, retry, throwError, timeout, timer } from 'rxjs';
import { HttpErrorResponse } from '@angular/common/http';

import { describeError } from './http-error';
import { WardGroup } from './models';
import { PatientApiService } from './patient-api.service';

/** After this many seconds, the UI tells the user the request is slow (not stuck). */
const SLOW_AFTER_SECONDS = 2;
/** Give up waiting after this long and offer a retry. */
const TIMEOUT_MS = 15000;

/**
 * State of the main page's patient list, kept outside the component so it survives navigation.
 *
 * How the deliberately slow endpoint is handled:
 * 1. **Cache (stale-while-revalidate)** — after the first load the last result is shown instantly
 *    when coming back to the page, while a fresh copy loads in the background.
 * 2. **Progress feedback** — skeleton placeholders on first load; after 2s a "still loading"
 *    notice with an elapsed-seconds counter, so the user knows the app isn't frozen.
 * 3. **Timeout + retry** — gives up after 15s with a clear error and a Retry button;
 *    transient network / 5xx errors are retried once automatically.
 * 4. **De-duplication** — a load already in flight is reused, never started twice.
 * 5. **Isolation** — the patient page uses its own fast endpoint, so it never waits for this one.
 */
@Injectable({ providedIn: 'root' })
export class PatientListStore {
  private readonly api = inject(PatientApiService);

  readonly groups = signal<WardGroup[] | null>(null);
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);
  readonly lastUpdated = signal<Date | null>(null);
  readonly elapsedSeconds = signal(0);

  readonly hasData = computed(() => this.groups() !== null);
  readonly isSlow = computed(() => this.loading() && this.elapsedSeconds() >= SLOW_AFTER_SECONDS);
  readonly totalPatients = computed(() => this.groups()?.reduce((sum, g) => sum + g.patients.length, 0) ?? 0);

  private request?: Subscription;
  private ticker?: Subscription;

  /** Fetch a fresh list. Any cached list stays on screen until the new one arrives. */
  load(): void {
    if (this.request && !this.request.closed) return; // already loading — reuse it

    this.loading.set(true);
    this.error.set(null);
    this.startTicker();

    this.request = this.api
      .listByWard()
      .pipe(
        timeout(TIMEOUT_MS),
        retry({ count: 1, delay: (err) => (isTransient(err) ? timer(1000) : throwError(() => err)) }),
        finalize(() => {
          this.loading.set(false);
          this.ticker?.unsubscribe();
        }),
      )
      .subscribe({
        next: (groups) => {
          this.groups.set(groups);
          this.lastUpdated.set(new Date());
        },
        error: (err: unknown) => this.error.set(describeError(err)),
      });
  }

  /** Drop a deleted patient from the cached list, so it disappears without waiting for a reload. */
  forget(patientId: string): void {
    const groups = this.groups();
    if (!groups) return;
    this.groups.set(
      groups
        .map((g) => ({ ...g, patients: g.patients.filter((p) => p.id !== patientId) }))
        .filter((g) => g.patients.length > 0),
    );
  }

  /** Forget everything (on logout). */
  reset(): void {
    this.request?.unsubscribe();
    this.groups.set(null);
    this.error.set(null);
    this.lastUpdated.set(null);
  }

  private startTicker(): void {
    this.ticker?.unsubscribe();
    this.elapsedSeconds.set(0);
    const started = Date.now();
    this.ticker = timer(0, 250).subscribe(() => this.elapsedSeconds.set(Math.floor((Date.now() - started) / 1000)));
  }
}

/** Network failures and server errors may succeed on a second try; 4xx and timeouts won't. */
function isTransient(error: unknown): boolean {
  return error instanceof HttpErrorResponse && (error.status === 0 || error.status >= 500);
}
