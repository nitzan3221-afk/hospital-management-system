import { Routes } from '@angular/router';

import { authGuard, guestGuard, permissionGuard } from './core/auth.guards';
import { ShellComponent } from './layout/shell.component';

/**
 * Pages are lazy-loaded (each one is downloaded only when first opened).
 * Guards: authGuard = must be logged in; permissionGuard = role must allow the action.
 */
export const routes: Routes = [
  {
    path: 'login',
    canActivate: [guestGuard],
    title: 'Sign in · Ward Board',
    loadComponent: () => import('./pages/login/login.page').then((m) => m.LoginPage),
  },
  {
    path: '',
    component: ShellComponent,
    canActivate: [authGuard],
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'patients' },
      {
        path: 'patients',
        title: 'Patients · Ward Board',
        loadComponent: () => import('./pages/patient-list/patient-list.page').then((m) => m.PatientListPage),
      },
      {
        // Must come before 'patients/:id', otherwise "new" would be read as an ID
        path: 'patients/new',
        title: 'Add patient · Ward Board',
        canActivate: [permissionGuard('create_patient')],
        loadComponent: () => import('./pages/patient-form/patient-form.page').then((m) => m.PatientFormPage),
      },
      {
        path: 'patients/:id',
        title: 'Patient · Ward Board',
        loadComponent: () =>
          import('./pages/patient-detail/patient-detail.page').then((m) => m.PatientDetailPage),
      },
      {
        path: 'patients/:id/edit',
        title: 'Edit patient · Ward Board',
        canActivate: [permissionGuard('update_patient_info')],
        loadComponent: () => import('./pages/patient-form/patient-form.page').then((m) => m.PatientFormPage),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
