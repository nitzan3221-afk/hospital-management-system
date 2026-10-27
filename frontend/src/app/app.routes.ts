import { Routes } from '@angular/router';

import { authGuard, guestGuard } from './core/auth.guards';
import { ShellComponent } from './layout/shell.component';

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
    ],
  },
  { path: '**', redirectTo: '' },
];
