import { DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';

import { TimelineEvent, TimelineEventType } from '../../core/models';

type Tone = 'primary' | 'info' | 'success' | 'warning' | 'muted';

const EVENT_META: Record<TimelineEventType, { label: string; tone: Tone }> = {
  admitted: { label: 'Admitted', tone: 'primary' },
  doctor_visit: { label: 'Doctor visit', tone: 'info' },
  medication_prescribed: { label: 'Medication prescribed', tone: 'info' },
  medication_given: { label: 'Medication given', tone: 'success' },
  vitals_recorded: { label: 'Vitals recorded', tone: 'muted' },
  diagnosis_changed: { label: 'Diagnosis changed', tone: 'warning' },
  patient_updated: { label: 'Details updated', tone: 'muted' },
};

interface Day {
  key: string;
  date: Date;
  events: TimelineEvent[];
}

/**
 * Chronological feed of everything that happened to the patient, grouped by day.
 * Presentational only: receives the events, has no API access.
 */
@Component({
  selector: 'app-timeline',
  imports: [DatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <section class="card">
      <div class="card-head">
        <h2>Timeline</h2>
        <button type="button" class="btn btn-sm btn-ghost" (click)="newestFirst.set(!newestFirst())">
          {{ newestFirst() ? 'Newest first' : 'Oldest first' }} ⇅
        </button>
      </div>

      @for (day of days(); track day.key) {
        <h3 class="day">{{ day.date | date: 'EEEE, d MMM y' }}</h3>
        <ol class="events">
          @for (event of day.events; track event.id) {
            <li class="event tone-{{ meta[event.type].tone }}">
              <span class="dot" aria-hidden="true"></span>
              <div class="event-body">
                <div class="event-top">
                  <span class="event-type">{{ meta[event.type].label }}</span>
                  <time [attr.datetime]="event.at">{{ event.at | date: 'HH:mm' }}</time>
                </div>
                <p>{{ event.summary }}</p>
                <span class="muted small">by {{ event.by }}</span>
              </div>
            </li>
          }
        </ol>
      } @empty {
        <p class="muted">No events yet.</p>
      }
    </section>
  `,
  styles: `
    .day {
      margin: 18px 0 8px;
      font-size: 0.8rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--muted);
    }
    .events {
      list-style: none;
      margin: 0;
      padding: 0 0 0 6px;
    }
    .event {
      position: relative;
      display: flex;
      gap: 14px;
      padding-bottom: 14px;
    }
    /* vertical line connecting the dots */
    .event::before {
      content: '';
      position: absolute;
      left: 5px;
      top: 14px;
      bottom: 0;
      width: 2px;
      background: var(--border);
    }
    .event:last-child::before {
      display: none;
    }
    .dot {
      flex: none;
      width: 12px;
      height: 12px;
      margin-top: 4px;
      border-radius: 50%;
      background: var(--tone);
      box-shadow: 0 0 0 3px var(--surface);
      z-index: 1;
    }
    .event-body p {
      margin: 2px 0;
    }
    .event-top {
      display: flex;
      justify-content: space-between;
      gap: 12px;
    }
    .event-type {
      font-weight: 600;
      color: var(--tone);
    }
    time {
      color: var(--muted);
      font-size: 0.85rem;
      font-variant-numeric: tabular-nums;
    }
    .tone-primary { --tone: var(--primary); }
    .tone-info { --tone: var(--info); }
    .tone-success { --tone: var(--success); }
    .tone-warning { --tone: var(--warning); }
    .tone-muted { --tone: var(--muted); }
  `,
})
export class TimelineComponent {
  readonly events = input.required<TimelineEvent[]>();

  protected readonly meta = EVENT_META;
  /** Default is chronological (oldest first); the user can flip it. */
  protected readonly newestFirst = signal(false);

  protected readonly days = computed<Day[]>(() => {
    const sorted = [...this.events()].sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime());
    if (this.newestFirst()) sorted.reverse();

    const days: Day[] = [];
    for (const event of sorted) {
      const date = new Date(event.at);
      const key = date.toDateString();
      const current = days.at(-1);
      if (current?.key === key) {
        current.events.push(event);
      } else {
        days.push({ key, date, events: [event] });
      }
    }
    return days;
  });
}
