/**
 * Dashboard — redirects to the role-appropriate landing page.
 *
 * This component renders only when the user is authenticated (RequireAuth
 * wraps it in the router). It reads the role from the decoded token and
 * redirects immediately to the correct landing page.
 *
 * Why this exists: the root path "/" lands here. After login the user
 * is sent to their role-specific URL directly. But if someone navigates
 * to "/" directly while already logged in, this handles the redirect.
 */

import { Navigate } from 'react-router-dom';
import { useCurrentUser } from '../hooks/useCurrentUser';
import { ROLE_DEFAULT_ROUTES } from '../types';

export default function Dashboard() {
  const user = useCurrentUser();
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={ROLE_DEFAULT_ROUTES[user.role]} replace />;
}
