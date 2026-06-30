/**
 * AppHeader — shared top bar rendered on every authenticated page.
 *
 * Design choice — mounted inside route guards, not per-page:
 *   Every protected route already passes through RequireAuth or RequireRole.
 *   Rendering AppHeader there means every current and future protected page
 *   gets logout "for free" — no page component needs to import or render it.
 *   This guarantees the rule "every authenticated user can log out from any
 *   page" can never be violated by a page that forgets to include it.
 *
 * Design choice — role badge instead of full_name:
 *   The JWT payload is { user_id, role, exp } — no full_name is encoded in
 *   the token (encoding it would mean stale names until next login). Showing
 *   the role badge is information already available client-side with zero
 *   extra requests. Pages that need full_name fetch it themselves from their
 *   own user/profile endpoint.
 */

import { useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { logout } from '../services/auth';
import { useCurrentUser } from '../hooks/useCurrentUser';

const ROLE_LABELS: Record<string, string> = {
  client: 'Client',
  fitness_trainer: 'Fitness Trainer',
  nutritionist: 'Nutritionist',
  master_coach: 'Master Coach',
  super_admin: 'Super Admin',
};

const ROLE_COLOURS: Record<string, string> = {
  client: 'bg-blue-100 text-blue-800',
  fitness_trainer: 'bg-green-100 text-green-800',
  nutritionist: 'bg-purple-100 text-purple-800',
  master_coach: 'bg-orange-100 text-orange-800',
  super_admin: 'bg-red-100 text-red-800',
};

export function AppHeader() {
  const user = useCurrentUser();
  const navigate = useNavigate();
  const [loggingOut, setLoggingOut] = useState(false);

  if (!user) return null;

  async function handleLogout() {
    setLoggingOut(true);
    await logout(); // best-effort server call + clears tokenStore — see auth.ts
    navigate('/login', { replace: true });
  }

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
      <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">
        <span className="text-sm font-bold text-gray-900">Food 'n' Reps</span>

        <div className="flex items-center gap-3">
          <span
            className={`inline-flex px-2 py-0.5 rounded text-xs font-semibold ${
              ROLE_COLOURS[user.role] ?? 'bg-gray-100 text-gray-800'
            }`}
          >
            {ROLE_LABELS[user.role] ?? user.role}
          </span>
          <button
            onClick={handleLogout}
            disabled={loggingOut}
            className="text-sm font-medium text-gray-600 hover:text-red-600 disabled:opacity-50"
          >
            {loggingOut ? 'Logging out…' : 'Log out'}
          </button>
        </div>
      </div>
    </header>
  );
}
