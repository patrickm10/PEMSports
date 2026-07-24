import { describe, expect, it } from 'vitest';
import { staticAssetUrl } from './backendOrigin';

describe('staticAssetUrl', () => {
  it('passes through absolute http(s) CDN URLs unchanged', () => {
    const cdn =
      'https://a.espncdn.com/combiner/i?img=/i/headshots/nfl/players/full/3918298.png&h=96&w=96&scale=crop';
    expect(staticAssetUrl(cdn)).toBe(cdn);
    expect(staticAssetUrl('http://example.com/x.jpg')).toBe('http://example.com/x.jpg');
  });

  it('prefixes relative paths with backend origin in dev', () => {
    const url = staticAssetUrl('/headshots/abc.jpg');
    expect(url).toContain('/headshots/abc.jpg');
  });
});
