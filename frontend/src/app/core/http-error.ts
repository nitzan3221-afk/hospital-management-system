import { HttpErrorResponse } from '@angular/common/http';
import { TimeoutError } from 'rxjs';

/**
 * Turn any HTTP/RxJS error into a short message for the user.
 * Includes the backend's request ID (X-Request-ID) so a support engineer can find the
 * matching server log line.
 */
export function describeError(error: unknown): string {
  if (error instanceof TimeoutError) {
    return 'The server is taking too long to respond.';
  }
  if (!(error instanceof HttpErrorResponse)) {
    return 'Something went wrong.';
  }
  if (error.status === 0) {
    return 'Cannot reach the server. Check that the backend is running.';
  }

  const detail = error.error?.detail;
  let message: string;
  if (typeof detail === 'string') {
    message = detail;
  } else if (Array.isArray(detail) && detail.length) {
    // FastAPI validation errors: [{ loc: [...], msg: '...' }]
    message = detail
      .map((d: { loc?: unknown[]; msg?: string }) => `${String(d.loc?.at(-1) ?? 'field')}: ${d.msg}`)
      .join('; ');
  } else {
    message = `Request failed (${error.status}).`;
  }

  const requestId = error.headers?.get('X-Request-ID');
  return requestId ? `${message} (ref: ${requestId.slice(0, 8)})` : message;
}
