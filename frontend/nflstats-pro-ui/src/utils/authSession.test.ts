import { describe, expect, it } from 'vitest';
import { parseAuthDetail } from '../api/authApi';
import { guestCanEnterRankings, sessionStatusCopy } from './authSession';

describe('parseAuthDetail', () => {
  it('reads FastAPI string detail', () => {
    expect(parseAuthDetail({ detail: 'Incorrect email or password' }, 'fallback')).toBe(
      'Incorrect email or password',
    );
  });

  it('reads 422 validation msg arrays', () => {
    expect(
      parseAuthDetail(
        { detail: [{ loc: ['body', 'password'], msg: 'String should have at least 8 characters', type: 'string_too_short' }] },
        'fallback',
      ),
    ).toBe('String should have at least 8 characters');
  });

  it('uses fallback when payload is empty', () => {
    expect(parseAuthDetail(null, 'Could not create the account.')).toBe(
      'Could not create the account.',
    );
  });
});

describe('guest launch vs /auth/me', () => {
  it('never blocks rankings entry on session restore', () => {
    expect(guestCanEnterRankings()).toBe(true);
  });

  it('tells guests they can enter while /me is in flight', () => {
    expect(sessionStatusCopy(true, false)).toContain('You can enter now');
    expect(sessionStatusCopy(false, false)).toContain('does not unlock different rankings');
  });
});
