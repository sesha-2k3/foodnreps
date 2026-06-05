/**
 * Login page — the public entry point for all roles.
 *
 * After a successful login the backend returns an access token (in the JSON
 * body) and sets a refresh token cookie. We store the access token in the
 * memory store and decode it to determine which dashboard to redirect to.
 *
 * Design choice — role-based redirect in the login handler, not a generic /dashboard:
 *   Each role has a distinct landing page. A fitness trainer landing on the
 *   client dashboard would see an empty page with no useful actions. The role
 *   is available immediately after decoding the just-issued token.
 */

import { useState, type FormEvent } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import { api } from '../services/api';
import { tokenStore } from '../services/auth';
import { useCurrentUser } from '../hooks/useCurrentUser';
import { ROLE_DEFAULT_ROUTES, type TokenResponse } from '../types';

export default function Login() {
  const navigate = useNavigate();
  const user = useCurrentUser();

  // Already authenticated — send to their dashboard
  if (user) return <Navigate to={ROLE_DEFAULT_ROUTES[user.role]} replace />;

  const [email, setEmail]       = useState('');
  const [password, setPassword] = useState('');
  const [error, setError]       = useState<string | null>(null);
  const [loading, setLoading]   = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await api.post<TokenResponse>('/auth/login', { email, password });
      tokenStore.set(res.data.access_token);

      // Decode the token to get the role for routing
      const { jwtDecode } = await import('jwt-decode');
      const payload = jwtDecode<{ role: string }>(res.data.access_token);
      const role = payload.role as keyof typeof ROLE_DEFAULT_ROUTES;
      navigate(ROLE_DEFAULT_ROUTES[role] ?? '/', { replace: true });
    } catch (err: unknown) {
      if (
        err &&
        typeof err === 'object' &&
        'response' in err &&
        err.response &&
        typeof err.response === 'object' &&
        'data' in err.response &&
        err.response.data &&
        typeof err.response.data === 'object' &&
        'detail' in err.response.data
      ) {
        setError(String((err.response as { data: { detail: string } }).data.detail));
      } else {
        setError('Unable to reach the server. Check that the backend is running.');
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-sm">
        {/* Logo / title */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Food 'n' Reps</h1>
          <p className="mt-2 text-sm text-gray-500">Sign in to your account</p>
        </div>

        {/* Card */}
        <div className="bg-white rounded-2xl shadow-sm border border-gray-200 p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Email address
              </label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={e => setEmail(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm
                           focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           placeholder:text-gray-400"
                placeholder="you@example.com"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Password
              </label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm
                           focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent
                           placeholder:text-gray-400"
                placeholder="••••••••"
              />
            </div>

            {error && (
              <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3">
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400
                         text-white text-sm font-medium rounded-lg transition-colors
                         focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
            >
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
