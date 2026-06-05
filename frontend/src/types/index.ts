/**
 * Shared TypeScript types for Food 'n' Reps.
 *
 * UserRole values must match the backend's UserRole enum string values exactly.
 * Any mismatch causes JWT decode errors and broken role guards.
 */

export type UserRole =
  | 'client'
  | 'fitness_trainer'
  | 'nutritionist'
  | 'master_coach'
  | 'super_admin';

/**
 * The decoded access token payload, containing only what is needed
 * for client-side routing decisions. Verification is the backend's job;
 * the frontend decodes only to read the role and user ID claims.
 */
export interface CurrentUser {
  id: string;      // JWT `sub` claim — UUID string
  role: UserRole;  // JWT `role` claim
}

/**
 * The JSON body returned by POST /auth/login and POST /auth/refresh.
 * The refresh token is NOT in this body — it is an httpOnly cookie
 * set by the backend response and never visible to JavaScript.
 */
export interface TokenResponse {
  access_token: string;
  token_type: string;
}

/** Maps each role to its post-login landing route. */
export const ROLE_DEFAULT_ROUTES: Record<UserRole, string> = {
  client:          '/client/dashboard',
  fitness_trainer: '/trainer/clients',
  nutritionist:    '/nutritionist/clients',
  master_coach:    '/coach/clients',
  super_admin:     '/admin/users',
};
