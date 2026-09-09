import { afterEach, describe, expect, it, vi } from 'vitest';
import { apiFetch, refreshSession } from './apiClient';

describe('apiClient', () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it('sends credentials on authenticated fetches', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    vi.stubGlobal('fetch', fetchMock);

    await apiFetch('https://api.example.com/api/v1/insights');

    expect(fetchMock).toHaveBeenCalledWith(
      'https://api.example.com/api/v1/insights',
      { credentials: 'include' },
    );
  });

  it('retries once after refreshing on 401', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 401 })
      .mockResolvedValueOnce({ ok: true, status: 200 })
      .mockResolvedValueOnce({ ok: true, status: 200 });
    vi.stubGlobal('fetch', fetchMock);

    const response = await apiFetch('https://api.example.com/api/v1/players/p1/weekly');

    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect(fetchMock.mock.calls[1][0]).toContain('/auth/refresh');
    expect(fetchMock.mock.calls[1][1]).toMatchObject({
      method: 'POST',
      credentials: 'include',
    });
  });

  it('refreshSession posts to /auth/refresh with credentials', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200 });
    vi.stubGlobal('fetch', fetchMock);

    await refreshSession();

    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/auth/refresh'),
      expect.objectContaining({
        method: 'POST',
        credentials: 'include',
      }),
    );
  });
});
