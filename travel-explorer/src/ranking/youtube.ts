import type { QueryLang } from '../types';
import { cacheGet, cacheSet } from './cache';
import { YOUTUBE_LANG } from './queries';

export interface FetchedVideo {
  id: string;
  title: string;
  channel: string;
  views: number;
  /** title + description, used for name matching */
  text: string;
}

const API = 'https://www.googleapis.com/youtube/v3';
const TTL = 24 * 60 * 60 * 1000;
const MAX_RESULTS = 25;

async function call(path: string, params: Record<string, string>) {
  const res = await fetch(`${API}/${path}?${new URLSearchParams(params)}`);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    const reason: string | undefined = body?.error?.errors?.[0]?.reason;
    if (reason === 'quotaExceeded') throw new Error('YouTube daily search quota used up (resets at midnight Pacific Time)');
    if (reason === 'accessNotConfigured' || res.status === 403)
      throw new Error('YouTube Data API v3 is not enabled for this API key');
    throw new Error(body?.error?.message ?? `YouTube error ${res.status}`);
  }
  return body;
}

/**
 * One search ("best cafes in Kyoto") → up to 25 videos with full descriptions and view counts.
 * Costs 1 search.list call (100/day bucket) + 1 videos.list unit; cached for 24 h per query.
 */
export async function searchVideos(apiKey: string, q: string, lang: QueryLang): Promise<FetchedVideo[]> {
  const cacheKey = `travel-explorer:yt:${lang}:${q}`;
  const cached = cacheGet<FetchedVideo[]>(cacheKey);
  if (cached) return cached;

  const search = await call('search', {
    part: 'snippet',
    type: 'video',
    maxResults: String(MAX_RESULTS),
    q,
    relevanceLanguage: YOUTUBE_LANG[lang],
    key: apiKey,
  });
  const ids: string[] = (search.items ?? []).map((i: { id: { videoId: string } }) => i.id.videoId).filter(Boolean);
  if (ids.length === 0) return [];

  const details = await call('videos', { part: 'snippet,statistics', id: ids.join(','), key: apiKey });
  const videos: FetchedVideo[] = (details.items ?? []).map(
    (v: { id: string; snippet: { title: string; description: string; channelTitle: string }; statistics: { viewCount?: string } }) => ({
      id: v.id,
      title: v.snippet.title,
      channel: v.snippet.channelTitle,
      views: Number(v.statistics.viewCount ?? 0),
      text: `${v.snippet.title}\n${v.snippet.description.slice(0, 4000)}`,
    }),
  );
  cacheSet(cacheKey, videos, TTL);
  return videos;
}
