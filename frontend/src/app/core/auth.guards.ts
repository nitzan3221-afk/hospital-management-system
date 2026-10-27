import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';

import { AuthService } from './auth.service';
import { Permission } from './models';

/** Only logged-in users may enter; others go to /login and come back after logging in. */
export const authGuard: CanActivateFn = (_route, state) => {
  const auth = inject(AuthService);
  return auth.isAuthenticated()
    ? true
    : inject(Router).createUrlTree(['/login'], { queryParams: { returnUrl: state.url } });
};

/** Only users whose role grants ``permission`` may enter; others go back to the patient list. */
export function permissionGuard(permission: Permission): CanActivateFn {
  return () => {
    const auth = inject(AuthService);
    return auth.hasPermission(permission) ? true : inject(Router).createUrlTree(['/patients']);
  };
}

/** Logged-in users don't need the login page. */
export const guestGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  return auth.isAuthenticated() ? inject(Router).createUrlTree(['/patients']) : true;
};
