import { Directive, TemplateRef, ViewContainerRef, effect, inject, input } from '@angular/core';

import { AuthService } from './auth.service';
import { Permission } from './models';

/**
 * Renders its element only if the current user has the permission:
 *
 *   <button *appHasPermission="'prescribe_medication'">Prescribe</button>
 */
@Directive({ selector: '[appHasPermission]' })
export class HasPermissionDirective {
  readonly appHasPermission = input.required<Permission>();

  private readonly auth = inject(AuthService);
  private readonly template = inject(TemplateRef<unknown>);
  private readonly container = inject(ViewContainerRef);
  private rendered = false;

  constructor() {
    effect(() => {
      const allowed = this.auth.hasPermission(this.appHasPermission());
      if (allowed && !this.rendered) {
        this.container.createEmbeddedView(this.template);
        this.rendered = true;
      } else if (!allowed && this.rendered) {
        this.container.clear();
        this.rendered = false;
      }
    });
  }
}
