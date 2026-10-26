import { afterEach, describe, expect, it, vi } from 'vitest';
import { createLiveSignalProvider } from '../src/ranking/live';
import { rankPlaces } from '../src/ranking/rank';
import type { Place, RankContext } from '../src/types';

const places: Place[] = [
  { id: 'a', name: '清水寺', names: { en: 'Kiyomizu-dera', 'zh-TW': '清水寺' }, category: 'attractions', location: { lat: 0, lng: 0 }, rating: 4.6, ratingCount: 6000 },
  { id: 'b', name: '小咖啡', names: { en: 'Tiny Bean Coffee' }, category: 'attractions', location: { lat: 0, lng: 0 }, rating: 4.3, ratingCount: 200 },
];
const ctx: RankContext = { langs: ['en', 'zh-TW', 'ja'], cityByLang: { en: 'Kyoto', 'zh-TW': '京都' }, countryCode: 'JP', categories: ['attractions'] };

afterEach(() => vi.unstubAllGlobals());

function stubNetwork({ ytStatus = 200 } = {}) {
  const calls: string[] = [];
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    calls.push(url);
    if (url.includes('/youtube/v3/search')) {
      if (ytStatus !== 200) return Response.json({ error: { errors: [{ reason: 'quotaExceeded' }] } }, { status: ytStatus });
      return Response.json({ items: [{ id: { videoId: 'v1' } }, { id: { videoId: 'v2' } }] });
    }
    if (url.includes('/youtube/v3/videos')) {
      return Response.json({
        items: [
          { id: 'v1', snippet: { title: 'Kyoto in 3 days', description: 'Kiyomizudera at sunrise', channelTitle: 'Trav' }, statistics: { viewCount: '2000000' } },
          { id: 'v2', snippet: { title: '京都自由行', description: '清水寺、伏見稻荷', channelTitle: '旅人' }, statistics: { viewCount: '500000' } },
        ],
      });
    }
    if (url.startsWith('https://en.wikivoyage.org')) {
      const hit = decodeURIComponent(url).includes('Kiyomizu-dera');
      return Response.json({ query: { search: hit ? [{ title: 'Kyoto/Eastern' }] : [] } });
    }
    if (url === '/api/articles') {
      const body = JSON.parse(String(init?.body));
      return Response.json({ articles: [{ title: `Guide (${body.lang})`, url: 'https://blog.example/kyoto', matches: [0] }] });
    }
    return new Response('not found', { status: 404 });
  }));
  return calls;
}

describe('live signal provider', () => {
  it('collects videos (deduped across languages), Wikivoyage and articles, then ranks', async () => {
    const calls = stubNetwork();
    const provider = createLiveSignalProvider({ youtubeKey: 'yt', articlesEndpoint: '/api/articles' });
    const { places: ranked, report } = await rankPlaces(places, provider, ctx);
    const [a, b] = ranked;

    expect(report.available).toEqual({ video: true, articles: true, wikivoyage: true });
    expect(a.ranking!.signals.videos.map((v) => v.id)).toEqual(['v1', 'v2']); // English + Chinese mentions, sorted by views
    expect(a.ranking!.signals.wikivoyage?.url).toBe('https://en.wikivoyage.org/wiki/Kyoto%2FEastern');
    expect(a.ranking!.signals.articles).toHaveLength(1); // same article URL from 3 language queries counts once
    expect(a.ranking!.offMapSources).toBe(3);
    expect(b.ranking!.offMapSources).toBe(0);
    expect(a.ranking!.score).toBeGreaterThan(b.ranking!.score);

    // queries ran in English, Chinese and (city falls back to English) Japanese
    const ytQueries = calls.filter((u) => u.includes('/youtube/v3/search')).map((u) => new URL(u).searchParams.get('q'));
    expect(ytQueries).toEqual(['best things to do in Kyoto', '京都 景點 推薦', 'Kyoto 観光スポット おすすめ']);
  });

  it('leaves out signals that fail instead of counting them as zero', async () => {
    stubNetwork({ ytStatus: 403 });
    const provider = createLiveSignalProvider({ youtubeKey: 'yt' });
    const { places: ranked, report } = await rankPlaces(places, provider, ctx);
    expect(report.available.video).toBe(false);
    expect(report.available.articles).toBe(false);
    expect(report.notes.join(' ')).toMatch(/quota/);
    expect(ranked[0].ranking!.parts.video).toBeUndefined();
  });
});
