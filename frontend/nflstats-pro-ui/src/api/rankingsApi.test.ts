import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  ApiError,
  RankingsApi,
  REQUEST_TIMEOUT_MS,
  shouldRetryRankingsQuery,
} from './rankingsApi';

describe('shouldRetryRankingsQuery', () => {
  it('retries TimeoutError up to two failures', () => {
    const err = new Error('TimeoutError');
    err.name = 'TimeoutError';
    expect(shouldRetryRankingsQuery(0, err)).toBe(true);
    expect(shouldRetryRankingsQuery(1, err)).toBe(true);
    expect(shouldRetryRankingsQuery(2, err)).toBe(false);
  });

  it('does not retry parent AbortError', () => {
    const err = new Error('Aborted');
    err.name = 'AbortError';
    expect(shouldRetryRankingsQuery(0, err)).toBe(false);
  });

  it('does not retry 4xx', () => {
    expect(shouldRetryRankingsQuery(0, new ApiError('HTTP 404', 404))).toBe(false);
    expect(shouldRetryRankingsQuery(0, new ApiError('HTTP 422', 422))).toBe(false);
  });

  it('retries 5xx until failureCount 2', () => {
    const err = new ApiError('HTTP 503', 503);
    expect(shouldRetryRankingsQuery(0, err)).toBe(true);
    expect(shouldRetryRankingsQuery(1, err)).toBe(true);
    expect(shouldRetryRankingsQuery(2, err)).toBe(false);
  });
});

describe('fetchWithTimeout', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it('uses a timeout long enough for Render free-tier wake', () => {
    expect(REQUEST_TIMEOUT_MS).toBeGreaterThanOrEqual(30_000);
  });

  it('throws TimeoutError after the client timeout, not AbortError', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init?: RequestInit) => {
        return new Promise((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () => {
            reject(Object.assign(new Error('Aborted'), { name: 'AbortError' }));
          });
        });
      }),
    );

    const pending = RankingsApi.fetchSeasons('qb');
    const assertion = expect(pending).rejects.toMatchObject({ name: 'TimeoutError' });
    await vi.advanceTimersByTimeAsync(REQUEST_TIMEOUT_MS);
    await assertion;
  });

  it('does not convert a parent abort into TimeoutError', async () => {
    vi.useRealTimers();
    vi.stubGlobal(
      'fetch',
      vi.fn((_url: string, init?: RequestInit) => {
        return new Promise((_resolve, reject) => {
          init?.signal?.addEventListener('abort', () => {
            reject(Object.assign(new Error('Aborted'), { name: 'AbortError' }));
          });
        });
      }),
    );

    const parent = new AbortController();
    const pending = RankingsApi.fetchSeasons('qb', parent.signal);
    parent.abort();
    await expect(pending).rejects.toMatchObject({ name: 'AbortError' });
  });
});
