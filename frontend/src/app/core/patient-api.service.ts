import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import {
  MedicationCreate,
  PatientCreate,
  PatientDetail,
  PatientInfo,
  VitalsCreate,
  WardGroup,
} from './models';

/** Thin, typed wrapper around the backend's /api/patients endpoints. */
@Injectable({ providedIn: 'root' })
export class PatientApiService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api/patients';

  /** Deliberately slow on the backend (simulated heavy overview query). */
  listByWard(): Observable<WardGroup[]> {
    return this.http.get<WardGroup[]>(this.base);
  }

  get(id: string): Observable<PatientDetail> {
    return this.http.get<PatientDetail>(`${this.base}/${id}`);
  }

  create(patient: PatientCreate): Observable<PatientDetail> {
    return this.http.post<PatientDetail>(this.base, patient);
  }

  update(id: string, changes: Partial<PatientInfo>): Observable<PatientDetail> {
    return this.http.patch<PatientDetail>(`${this.base}/${id}`, changes);
  }

  delete(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/${id}`);
  }

  changeDiagnosis(id: string, diagnosis: string): Observable<PatientDetail> {
    return this.http.put<PatientDetail>(`${this.base}/${id}/diagnosis`, { diagnosis });
  }

  prescribe(id: string, medication: MedicationCreate): Observable<PatientDetail> {
    return this.http.post<PatientDetail>(`${this.base}/${id}/medications`, medication);
  }

  giveMedication(id: string, medicationId: string): Observable<PatientDetail> {
    return this.http.post<PatientDetail>(`${this.base}/${id}/medications/${medicationId}/give`, {});
  }

  recordVitals(id: string, vitals: VitalsCreate): Observable<PatientDetail> {
    return this.http.post<PatientDetail>(`${this.base}/${id}/vitals`, vitals);
  }
}
