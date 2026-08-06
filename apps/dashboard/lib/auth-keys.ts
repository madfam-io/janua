/**
 * Auth storage key names — the single source of truth, shared by the edge
 * middleware and the browser code.
 *
 * Deliberately DOM-free and dependency-free so `middleware.ts` (edge runtime)
 * can import it. Browser-only helpers live in `./auth-storage`, which imports
 * from here.
 *
 * WHY THIS EXISTS: these strings were hand-written at five call sites and
 * drifted. The login page wrote `janua_access_token` (matching middleware),
 * while the post-login page and layout read `janua_token`. Middleware admitted
 * the user; the page found no cookie and redirected to /login; middleware
 * bounced them back — an infinite loop that looked like a frozen loading
 * screen after a SUCCESSFUL login, with nothing logged on either side.
 *
 * Because middleware.ts and the pages now import the SAME constant, that
 * divergence is a compile error rather than a silent redirect loop. Keep it
 * that way: import these names, never re-type them.
 */

/** Session cookie the middleware gates every request on. */
export const AUTH_COOKIE = 'janua_access_token'

/** localStorage key holding the SDK's access token. */
export const ACCESS_TOKEN_KEY = 'janua_access_token'

/** localStorage key holding the refresh token. */
export const REFRESH_TOKEN_KEY = 'janua_refresh_token'

/** localStorage key holding the access-token expiry timestamp. */
export const TOKEN_EXPIRES_AT_KEY = 'janua_token_expires_at'

/** localStorage key holding the serialized user object. */
export const USER_KEY = 'janua_user'

/** Cookie domain suffix so the session is shared across *.janua.dev hosts. */
export const COOKIE_DOMAIN_SUFFIX = 'janua.dev'
