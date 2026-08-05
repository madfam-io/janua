/**
 * Client-side mirror of the server's password policy
 * (apps/api/app/services/auth_service.py::validate_password_strength).
 *
 * The sign-up form previously gated on a heuristic strength score (>= 50),
 * which accepts passwords the server then rejects with a 400 — the user was
 * told (at best) something vague after a round-trip. Validating the exact
 * policy client-side gives the precise unmet rule before submission; the
 * server remains the authority.
 */

export const PASSWORD_SPECIAL_CHARS = '!@#$%^&*()_+-=[]{}|;:,.<>?'

export interface PasswordPolicyResult {
  ok: boolean
  /** Human-readable unmet requirements, in server-check order. */
  failures: string[]
}

export function validatePasswordPolicy(password: string): PasswordPolicyResult {
  const failures: string[] = []

  if (password.length < 12) {
    failures.push('At least 12 characters')
  }
  if (!/[A-Z]/.test(password)) {
    failures.push('At least one uppercase letter')
  }
  if (!/[a-z]/.test(password)) {
    failures.push('At least one lowercase letter')
  }
  if (!/\d/.test(password)) {
    failures.push('At least one number')
  }
  // Array.from, not [...password]: spreading a string requires
  // --downlevelIteration under the consuming apps' TS target, and this module
  // is compiled by each app (dashboard/admin/website), not prebuilt. The
  // spread form type-checked only while the module was unreachable from the
  // package entrypoint — it broke the dashboard build the moment the export
  // was wired up correctly.
  if (!Array.from(password).some((c) => PASSWORD_SPECIAL_CHARS.includes(c))) {
    failures.push(`At least one special character (${PASSWORD_SPECIAL_CHARS})`)
  }

  return { ok: failures.length === 0, failures }
}
