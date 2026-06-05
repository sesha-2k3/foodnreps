/**
 * Application entry point — loading gate + QueryClient + RouterProvider.
 *
 * Design choice — loading gate fires before RouterProvider renders:
 *   On every page load (including refresh), the app fires POST /auth/refresh
 *   before rendering any route. This silently restores the access token if
 *   the httpOnly refresh cookie is still valid. Without this gate, a page
 *   refresh clears the in-memory access token and every route guard redirects
 *   to /login — even if the session is perfectly valid for another 7 days.
 *
 *   The gate does not redirect on failure. If the refresh fails (no cookie,
 *   expired cookie), `tokenStore` remains null, `ready` is set to true, the
 *   router renders, and the route guard for the current path handles the
 *   redirect to /login. This separation of concerns means the gate has one
 *   job: restore the token if possible. The guard has one job: enforce auth.
 *
 * Design choice — QueryClient at the root wrapping RouterProvider:
 *   TanStack Query's QueryClientProvider must be above any component that
 *   uses useQuery or useMutation. Placing it above RouterProvider ensures
 *   it is available in every route without needing it in individual pages.
 *
 * Design choice — StrictMode enabled:
 *   React StrictMode double-invokes effects in development to surface
 *   unintentional side effects. The loading gate runs twice in dev —
 *   the second refresh call is cheap (200ms, one cookie check) and the
 *   second token overwrites the first cleanly. Disabling StrictMode to
 *   avoid this would hide real bugs.
 */

import { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { api } from './services/api';
import { tokenStore } from './services/auth';
import { router } from './router';
import type { TokenResponse } from './types';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      /**
       * retry: 1 — not the default 3.
       * 401/403 errors are not transient; retrying produces the same result.
       * 1 retry handles genuine flaky network responses without hammering a
       * server that is intentionally rejecting the request.
       */
      retry: 1,

      /**
       * staleTime: 5 minutes.
       * Workout programmes and diet plans change infrequently — a coach
       * does not update prescriptions every 30 seconds. Treating data as
       * stale immediately (the default) causes unnecessary refetches on
       * every window focus event, producing visible loading states for no
       * benefit. 5 minutes matches the access token lifetime.
       */
      staleTime: 5 * 60 * 1000,

      /**
       * refetchOnWindowFocus: false.
       * The default is true. For this application's data (training plans,
       * diet entries), a background refetch on every tab switch creates
       * loading spinners with no value. Enable per-query if a specific
       * data type requires it.
       */
      refetchOnWindowFocus: false,
    },
  },
});

// ── Loading spinner ────────────────────────────────────────────────────────────

function LoadingSpinner() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin" />
        <p className="text-sm text-gray-500">Loading…</p>
      </div>
    </div>
  );
}

// ── App root with loading gate ─────────────────────────────────────────────────

function App() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    api
      .post<TokenResponse>('/auth/refresh')
      .then(res => tokenStore.set(res.data.access_token))
      .catch(() => {
        // No valid refresh cookie — tokenStore stays null.
        // The route guard will redirect to /login on the first protected route.
      })
      .finally(() => setReady(true));
  }, []);

  if (!ready) return <LoadingSpinner />;

  return (
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  );
}

// ── Mount ──────────────────────────────────────────────────────────────────────

const root = document.getElementById('root');
if (!root) throw new Error('Root element #root not found in index.html');

createRoot(root).render(
    <App />
);
