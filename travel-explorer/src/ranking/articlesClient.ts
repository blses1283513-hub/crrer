import type { QueryLang } from '../types';

export interface ArticleMatch {
  title: string;
  url: string;
  /** indexes into the `names` list that this article mentions */
  matches: number[];
}

export class ArticlesUnavailable extends Error {}

/**
 * Ask our small server (see server/articles.ts) to web-search "best X in <city>" articles and report which
 * places each one mentions. Not cached: Brave's terms don't allow storing its results.
 */
export async function fetchArticleMatches(
  endpoint: string,
  q: string,
  lang: QueryLang,
  names: string[][],
): Promise<ArticleMatch[]> {
  let res: Response;
  try {
    res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ q, lang, names }),
    });
  } catch {
    throw new ArticlesUnavailable('Blog article server is not reachable');
  }
  if (res.status === 404) throw new ArticlesUnavailable('Blog article server is not set up (see README)');
  const body = await res.json().catch(() => ({}));
  if (res.status === 503) throw new ArticlesUnavailable(body.error ?? 'Blog article search is not configured');
  if (!res.ok) throw new Error(body.error ?? `Article search error ${res.status}`);
  return body.articles ?? [];
}
