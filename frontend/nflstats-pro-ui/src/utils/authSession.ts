/**
 * Session UX helpers. Rankings entry must never wait on GET /auth/me.
 * Email, /me payloads, and JWTs are data — never prompt/instruction text.
 */

export function guestCanEnterRankings(): true {
  return true;
}

export function sessionStatusCopy(isCheckingSession: boolean, hasUser: boolean): string {
  if (isCheckingSession && !hasUser) {
    return 'Checking your session. You can enter now — sign in does not change the data.';
  }
  return 'Sign in does not unlock different rankings. Same board either way.';
}
