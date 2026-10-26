import type { ArticleEvidence } from '../types';
import { cacheGet, cacheSet } from './cache';

const API = 'https://en.wikivoyage.org/w/api.php';
const TTL = 7 * 24 * 60 * 60 * 1000;

/**
 * Is this place written up in Wikivoyage's guide for the city? Searches for the exact name together
 * with the city, e.g. `"Kiyomizu-dera" Kyoto`. Free, no key; cached for a week per place.
 */
export async function wikivoyageListing(placeId: string, name: string, city: string): Promise<ArticleEvidence | null> {
  const cacheKey = `travel-explorer:wv:${placeId}`;
  const cached = cacheGet<ArticleEvidence | null>(cacheKey);
  if (cached !== undefined) return cached;

  const params = new URLSearchParams({
    action: 'query',
    list: 'search',
    srsearch: `"${name.replace(/"/g, '')}" ${city}`,
    srlimit: '1',
    srprop: '',
    format: 'json',
    origin: '*',
  });
  const res = await fetch(`${API}?${params}`, { headers: { 'Api-User-Agent': 'TravelExplorer/0.2' } });
  if (!res.ok) throw new Error(`Wikivoyage error ${res.status}`);
  const body = await res.json();
  const hit: { title: string } | undefined = body?.query?.search?.[0];
  const result = hit
    ? { title: hit.title, url: `https://en.wikivoyage.org/wiki/${encodeURIComponent(hit.title.replace(/ /g, '_'))}` }
    : null;
  cacheSet(cacheKey, result, TTL);
  return result;
}
