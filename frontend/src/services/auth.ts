/**
 * Access token memory store and auth utilities.
 *
 * Design choice — module-level variable, not React state or localStorage:
 *   The access token must be accessible outside React's component tree —
 *   specifically inside the Axios response interceptor, which runs before
 *   any React rendering. React state (useState, Context) only exists within
 *   the component tree. localStorage is readable by XSS-injected scripts.
 *   A plain module-level variable is accessible only to code that explicitly
 *   imports this module, which no injected script can do.
 *
 * Design choice — three-method object, not three exported functions:
 *   Grouping as `tokenStore.get()`, `tokenStore.set()`, `tokenStore.clear()`
 *   makes the intent clear at the call site and makes the object easy to
 *   mock in tests: `vi.spyOn(tokenStore, 'get').mockReturnValue('fake-token')`.
 */

let _accessToken: string | null = null;

export const tokenStore = {
  get:   (): string | null => _accessToken,
  set:   (token: string): void => { _accessToken = token; },
  clear: (): void => { _accessToken = null; },
};

/**
 * Log out: call POST /auth/logout (which revokes the refresh token DB record
 * and clears the httpOnly cookie), then clear the in-memory access token.
 *
 * Import `api` lazily to avoid a circular import between api.ts ↔ auth.ts.
 * api.ts imports tokenStore from auth.ts; auth.ts importing api directly
 * would create a cycle. The dynamic import breaks the cycle cleanly.
 */
export async function logout(): Promise<void> {
  try {
    const { api } = await import('./api');
    await api.post('/auth/logout');
  } catch {
    // Logout is best-effort. Even if the server call fails (e.g. offline),
    // clearing the local token prevents further authenticated requests.
  } finally {
    tokenStore.clear();
  }
}
