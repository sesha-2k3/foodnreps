/**
 * useCurrentUser — returns the decoded current user from the access token.
 *
 * Design choice — decodes the JWT client-side, no server call:
 *   The JWT payload contains user_id (sub) and role, signed by the backend.
 *   The backend already verified these when it issued the token. The client
 *   decodes only to read the claims for routing decisions — it does not
 *   re-verify the signature (it cannot, and does not need to). Any tampering
 *   with the token would be caught by the backend on the next API call.
 *
 * Design choice — returns null instead of throwing:
 *   An unauthenticated state is expected (login page, loading gate not yet
 *   complete). Null is a valid, representable state. Throwing would require
 *   every caller to wrap in try/catch for a routine scenario.
 *
 * Design choice — no React state, just reading from tokenStore:
 *   The token changes at most a few times per session (login, refresh, logout).
 *   Re-renders driven by token changes happen naturally: login sets the token
 *   then navigates, causing a remount. There is no need for reactive state
 *   tracking here. If this becomes necessary, wrap tokenStore in Zustand.
 */

import { jwtDecode } from 'jwt-decode';
import { tokenStore } from '../services/auth';
import type { CurrentUser, UserRole } from '../types';

interface JwtPayload {
  sub: string;
  role: string;
  exp: number;
  type: string;
}

export function useCurrentUser(): CurrentUser | null {
  const token = tokenStore.get();
  if (!token) return null;

  try {
    const payload = jwtDecode<JwtPayload>(token);
    return {
      id: payload.sub,
      role: payload.role as UserRole,
    };
  } catch {
    // Malformed token in memory — treat as unauthenticated
    return null;
  }
}
