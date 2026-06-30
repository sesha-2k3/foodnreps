/**
 * Route guard components.
 *
 * Design choice — guards as wrapper components, not HOCs or hooks:
 *   `<RequireRole roles={['client']}><WorkoutView /></RequireRole>` reads
 *   exactly like what it does: "render WorkoutView only if role is client".
 *   Higher-order components obscure the component identity in React DevTools.
 *   A guard hook (`useRequireRole`) would need an effect + navigate, making
 *   every guarded page responsible for its own redirection. Wrapper components
 *   centralise the redirect decision.
 *
 * Design choice — RequireAuth and RequireRole are separate components:
 *   /personal/* routes accept any authenticated role — they use RequireAuth.
 *   Role-specific routes use RequireRole. If they were one component, a
 *   "no role restriction" case would need a sentinel value (empty array?
 *   undefined?), making call sites ambiguous. Two components is clearer.
 *
 * Design choice — replace: true on Navigate:
 *   The login redirect is not a user-navigated page that belongs in history.
 *   After login, pressing Back should not send the user back to the login
 *   page they were redirected away from.
 *
 * Design choice — AppHeader rendered here, not in individual pages:
 *   Every protected route passes through one of these two guards. Rendering
 *   AppHeader (which contains the logout button) at this single chokepoint
 *   guarantees every current and future protected page has a working logout
 *   option with zero per-page wiring. A page component can never "forget"
 *   to include it because it never imports it directly.
 */

import { Navigate } from 'react-router-dom';
import { useCurrentUser } from '../hooks/useCurrentUser';
import { AppHeader } from '../components/AppHeader';
import type { ReactElement } from 'react';
import type { UserRole } from '../types';

interface RequireAuthProps {
  children: ReactElement;
}

/**
 * Passes through to children if the user is authenticated.
 * Redirects to /login if not.
 * Use for routes accessible to any authenticated role (/personal/*).
 */
export function RequireAuth({ children }: RequireAuthProps): ReactElement {
  const user = useCurrentUser();
  if (!user) return <Navigate to="/login" replace />;
  return (
    <>
      <AppHeader />
      {children}
    </>
  );
}

interface RequireRoleProps {
  roles: UserRole[];
  children: ReactElement;
}

/**
 * Passes through to children if the user is authenticated AND has one
 * of the listed roles. Redirects to /login if not authenticated,
 * /unauthorized if authenticated but wrong role.
 *
 * Usage:
 *   <RequireRole roles={['client']}><WorkoutView /></RequireRole>
 *   <RequireRole roles={['fitness_trainer', 'master_coach']}><ProgramBuilder /></RequireRole>
 */
export function RequireRole({ roles, children }: RequireRoleProps): ReactElement {
  const user = useCurrentUser();
  if (!user) return <Navigate to="/login" replace />;
  if (!roles.includes(user.role)) return <Navigate to="/unauthorized" replace />;
  return (
    <>
      <AppHeader />
      {children}
    </>
  );
}
