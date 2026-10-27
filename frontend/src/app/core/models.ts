/** Types mirroring the backend API (see http://localhost:8000/docs). */

export type Role = 'doctor' | 'nurse' | 'secretary';

export type Permission =
  | 'read_patients'
  | 'create_patient'
  | 'update_patient_info'
  | 'delete_patient'
  | 'prescribe_medication'
  | 'give_medication'
  | 'record_vitals'
  | 'change_diagnosis';

export type Ward = 'ER' | 'INTERNAL_A' | 'INTERNAL_B' | 'ICU' | 'SURGERY' | 'PEDIATRICS';
export type HealthPlan = 'Clalit' | 'Maccabi' | 'Meuhedet' | 'Leumit';
export type Sex = 'male' | 'female';

export type TimelineEventType =
  | 'admitted'
  | 'doctor_visit'
  | 'medication_prescribed'
  | 'medication_given'
  | 'vitals_recorded'
  | 'diagnosis_changed'
  | 'patient_updated';

export interface User {
  username: string;
  full_name: string;
  role: Role;
  permissions: Permission[];
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: User;
}

export interface PatientSummary {
  id: string;
  full_name: string;
  sex: Sex;
  age: number;
  ward: Ward;
  health_plan: HealthPlan;
  diagnosis: string;
  last_vitals_at: string | null;
  active_medications: number;
}

export interface WardGroup {
  ward: Ward;
  ward_name: string;
  patients: PatientSummary[];
}

export interface Vitals {
  heart_rate: number;
  bp_systolic: number;
  bp_diastolic: number;
  temperature: number;
  recorded_at: string;
  recorded_by: string;
}

export interface Medication {
  id: string;
  name: string;
  dose: string;
  frequency: string;
  active: boolean;
  prescribed_by: string;
  prescribed_at: string;
  last_given_at: string | null;
  last_given_by: string | null;
}

export interface TimelineEvent {
  id: string;
  type: TimelineEventType;
  at: string;
  by: string;
  summary: string;
  details: Record<string, unknown>;
}

export interface PatientDetail {
  id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  sex: Sex;
  birth_date: string;
  age: number;
  health_plan: HealthPlan;
  ward: Ward;
  ward_name: string;
  diagnosis: string;
  admitted_at: string;
  updated_at: string;
  latest_vitals: Vitals | null;
  vitals: Vitals[];
  medications: Medication[];
  timeline: TimelineEvent[];
}

export interface PatientInfo {
  first_name: string;
  last_name: string;
  sex: Sex;
  birth_date: string;
  health_plan: HealthPlan;
  ward: Ward;
}

export interface PatientCreate extends PatientInfo {
  id: string;
  diagnosis: string;
}

export interface MedicationCreate {
  name: string;
  dose: string;
  frequency: string;
}

export interface VitalsCreate {
  heart_rate: number;
  bp_systolic: number;
  bp_diastolic: number;
  temperature: number;
}

/** Display options for selects. */
export const WARDS: { value: Ward; label: string }[] = [
  { value: 'ER', label: 'Emergency (ER)' },
  { value: 'INTERNAL_A', label: 'Internal Medicine A' },
  { value: 'INTERNAL_B', label: 'Internal Medicine B' },
  { value: 'ICU', label: 'ICU' },
  { value: 'SURGERY', label: 'Surgery / Post-Op' },
  { value: 'PEDIATRICS', label: 'Pediatrics' },
];

export const HEALTH_PLANS: HealthPlan[] = ['Clalit', 'Maccabi', 'Meuhedet', 'Leumit'];

export const ROLE_LABELS: Record<Role, string> = {
  doctor: 'Doctor',
  nurse: 'Nurse',
  secretary: 'Secretary',
};
