import type { ArticleEvidence, Place, PlaceSignals, RankContext, SignalProvider, SignalReport, VideoEvidence } from '../types';
import { ArticlesUnavailable, fetchArticleMatches } from './articlesClient';
import { mentions, nameVariants, prepareText } from './match';
import { buildQuery } from './queries';
import { searchVideos, type FetchedVideo } from './youtube';
import { wikivoyageListing } from './wikivoyage';

export interface LiveOptions {
  youtubeKey?: string;
  articlesEndpoint?: string;
}

const message = (e: unknown) => (e instanceof Error ? e.message : String(e));

/** Run `fn` over `items` with at most `limit` in flight (Wikivoyage asks clients to be gentle). */
async function mapLimit<T, R>(items: T[], limit: number, fn: (t: T) => Promise<R>): Promise<PromiseSettledResult<R>[]> {
  const out: PromiseSettledResult<R>[] = new Array(items.length);
  let next = 0;
  const worker = async () => {
    while (next < items.length) {
      const i = next++;
      try {
        out[i] = { status: 'fulfilled', value: await fn(items[i]) };
      } catch (reason) {
        out[i] = { status: 'rejected', reason };
      }
    }
  };
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return out;
}

export function createLiveSignalProvider({ youtubeKey, articlesEndpoint }: LiveOptions): SignalProvider {
  return {
    kind: 'live',
    async collect(places: Place[], ctx: RankContext): Promise<SignalReport> {
      const notes: string[] = [];
      const byId = new Map<string, PlaceSignals>(places.map((p) => [p.id, { videos: [], articles: [] }]));
      const variants = places.map((p) => nameVariants([p.name, ...Object.values(p.names ?? {})]));
      const cityEn = ctx.cityByLang.en;

      const queries = ctx.categories.flatMap((cat) =>
        ctx.langs.flatMap((lang) => {
          const city = ctx.cityByLang[lang] ?? cityEn;
          return city ? [{ lang, q: buildQuery(lang, cat, city) }] : [];
        }),
      );
      if (queries.length === 0) notes.push('Could not tell which city this is, so videos and articles were skipped');

      const videoTask = async () => {
        if (!youtubeKey || queries.length === 0) return false;
        const settled = await Promise.allSettled(queries.map(({ q, lang }) => searchVideos(youtubeKey, q, lang)));
        const videos = new Map<string, FetchedVideo>();
        for (const r of settled) if (r.status === 'fulfilled') for (const v of r.value) videos.set(v.id, v);
        const failed = settled.find((r): r is PromiseRejectedResult => r.status === 'rejected');
        if (failed) notes.push(`Videos: ${message(failed.reason)}`);
        if (settled.every((r) => r.status === 'rejected')) return false;
        for (const v of videos.values()) {
          const text = prepareText(v.text);
          places.forEach((p, i) => {
            if (mentions(text, variants[i])) {
              const ev: VideoEvidence = { id: v.id, title: v.title, channel: v.channel, views: v.views, url: `https://www.youtube.com/watch?v=${v.id}` };
              byId.get(p.id)!.videos.push(ev);
            }
          });
        }
        return true;
      };

      const articleTask = async () => {
        if (!articlesEndpoint || queries.length === 0) return false;
        const settled = await Promise.allSettled(
          queries.map(({ q, lang }) => fetchArticleMatches(articlesEndpoint, q, lang, variants)),
        );
        const failed = settled.find((r): r is PromiseRejectedResult => r.status === 'rejected');
        if (failed) notes.push(`Blog articles: ${message(failed.reason)}`);
        if (settled.every((r) => r.status === 'rejected')) return false;
        const seen = new Map<string, Set<string>>(); // place id → article urls already counted
        for (const r of settled) {
          if (r.status !== 'fulfilled') continue;
          for (const a of r.value) {
            for (const idx of a.matches) {
              const p = places[idx];
              if (!p) continue;
              const urls = seen.get(p.id) ?? new Set<string>();
              if (urls.has(a.url)) continue;
              urls.add(a.url);
              seen.set(p.id, urls);
              const ev: ArticleEvidence = { title: a.title, url: a.url };
              byId.get(p.id)!.articles.push(ev);
            }
          }
        }
        return true;
      };

      const wikivoyageTask = async () => {
        if (!cityEn) return false;
        const settled = await mapLimit(places, 6, (p) => wikivoyageListing(p.id, p.names?.en ?? p.name, cityEn));
        if (settled.every((r) => r.status === 'rejected')) {
          if (settled.length) notes.push(`Wikivoyage: ${message((settled[0] as PromiseRejectedResult).reason)}`);
          return false;
        }
        settled.forEach((r, i) => {
          if (r.status === 'fulfilled' && r.value) byId.get(places[i].id)!.wikivoyage = r.value;
        });
        return true;
      };

      const [video, articles, wikivoyage] = await Promise.all([
        videoTask().catch((e) => (notes.push(`Videos: ${message(e)}`), false)),
        articleTask().catch((e) => (notes.push(`Blog articles: ${e instanceof ArticlesUnavailable ? e.message : message(e)}`), false)),
        wikivoyageTask().catch((e) => (notes.push(`Wikivoyage: ${message(e)}`), false)),
      ]);
      if (!youtubeKey) notes.push('Videos: no YouTube API key configured');
      if (!articlesEndpoint) notes.push('Blog articles: no article server configured');

      for (const s of byId.values()) s.videos.sort((a, b) => b.views - a.views);
      return { byId, available: { video, articles, wikivoyage }, notes };
    },
  };
}
