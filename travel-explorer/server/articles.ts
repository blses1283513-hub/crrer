// POST /api/articles — web-searches "best X in <city>" articles with Brave Search, reads the top pages,
// and reports which of the given places each article mentions. Runs on the server so the Brave key stays
// secret (and because Brave's API can't be called from a browser). Used by both the Vite dev server and
// the Cloudflare Worker in worker/index.ts. Nothing is stored: Brave's terms forbid keeping its results.

import { mentions, prepareText } from '../src/ranking/match';
import { BRAVE_LANG, isQueryLang } from '../src/ranking/queries';

export interface ArticlesEnv {
  BRAVE_API_KEY?: string;
  /** comma-separated origins allowed to call this endpoint, e.g. "https://my-app.example.com" */
  ALLOWED_ORIGINS?: string;
}

const BRAVE_URL = 'https://api.search.brave.com/res/v1/web/search';
const MAX_ARTICLES = 6;
const PAGE_TIMEOUT_MS = 6000;
const MAX_PAGE_BYTES = 1_500_000;

// Results that are maps, videos or social feeds rather than articles.
const SKIP_HOSTS = /(^|\.)(youtube\.com|youtu\.be|google\.[a-z.]+|facebook\.com|instagram\.com|tiktok\.com|x\.com|twitter\.com)$/i;

const json = (body: unknown, status = 200, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json', ...headers } });

interface Body {
  q: string;
  lang: string;
  names: string[][];
}

function validate(b: unknown): Body | string {
  const body = b as Partial<Body> | null;
  if (!body || typeof body.q !== 'string' || !body.q.trim() || body.q.length > 200) return 'q must be 1–200 characters';
  if (!isQueryLang(body.lang)) return 'unsupported lang';
  if (
    !Array.isArray(body.names) ||
    body.names.length > 200 ||
    !body.names.every((v) => Array.isArray(v) && v.length <= 12 && v.every((s) => typeof s === 'string' && s.length <= 120))
  )
    return 'names must be up to 200 lists of up to 12 short strings';
  return body as Body;
}

export function htmlToText(html: string): string {
  return html
    .replace(/<(script|style|noscript|svg|template)[\s\S]*?<\/\1>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&quot;/g, '"')
    .replace(/&#39;|&apos;/g, "'")
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(Number(n)))
    .replace(/&#x([0-9a-f]+);/gi, (_, n) => String.fromCodePoint(parseInt(n, 16)))
    .replace(/\s+/g, ' ');
}

function isPublicHttpUrl(raw: string): boolean {
  try {
    const u = new URL(raw);
    if (u.protocol !== 'https:' && u.protocol !== 'http:') return false;
    const h = u.hostname;
    // No IP literals or local names: we only want ordinary public websites.
    return !/^[\d.]+$/.test(h) && !h.includes(':') && h.includes('.') && !/(^|\.)(localhost|local|internal)$/i.test(h);
  } catch {
    return false;
  }
}

async function readPage(url: string, fetchImpl: typeof fetch): Promise<string> {
  const res = await fetchImpl(url, {
    headers: { 'User-Agent': 'TravelExplorer/0.2 (article mention check)', Accept: 'text/html' },
    redirect: 'follow',
    signal: AbortSignal.timeout(PAGE_TIMEOUT_MS),
  });
  if (!res.ok || !res.body || !/text\/html|text\/plain/i.test(res.headers.get('content-type') ?? '')) return '';
  const reader = res.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  while (size < MAX_PAGE_BYTES) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    size += value.length;
  }
  reader.cancel().catch(() => {});
  const all = new Uint8Array(size);
  let offset = 0;
  for (const c of chunks) {
    all.set(c, offset);
    offset += c.length;
  }
  return htmlToText(new TextDecoder().decode(all));
}

async function braveSearch(q: string, lang: string, key: string, fetchImpl: typeof fetch) {
  const attempt = (withLang: boolean) => {
    const params = new URLSearchParams({ q, count: '10', safesearch: 'moderate' });
    if (withLang) params.set('search_lang', lang);
    return fetchImpl(`${BRAVE_URL}?${params}`, {
      headers: { Accept: 'application/json', 'X-Subscription-Token': key },
    });
  };
  let res = await attempt(true);
  if (res.status === 422) res = await attempt(false); // language not supported by Brave: search without it
  if (!res.ok) throw new Error(`Brave Search error ${res.status}`);
  const body = (await res.json()) as { web?: { results?: { title: string; url: string; description?: string }[] } };
  return body.web?.results ?? [];
}

export async function handleArticles(req: Request, env: ArticlesEnv, fetchImpl: typeof fetch = fetch): Promise<Response> {
  const origin = req.headers.get('Origin');
  const allowed = env.ALLOWED_ORIGINS?.split(',').map((s) => s.trim()).filter(Boolean);
  if (allowed?.length && origin && !allowed.includes(origin)) return json({ error: 'origin not allowed' }, 403);
  if (req.method !== 'POST') return json({ error: 'POST only' }, 405, { Allow: 'POST' });
  if (!env.BRAVE_API_KEY) return json({ error: 'BRAVE_API_KEY is not set on the server' }, 503);

  const parsed = validate(await req.json().catch(() => null));
  if (typeof parsed === 'string') return json({ error: parsed }, 400);
  const { q, lang, names } = parsed;

  let results;
  try {
    results = await braveSearch(q, BRAVE_LANG[lang as keyof typeof BRAVE_LANG], env.BRAVE_API_KEY, fetchImpl);
  } catch (e) {
    return json({ error: (e as Error).message }, 502);
  }

  const picked = results
    .filter((r) => isPublicHttpUrl(r.url) && !SKIP_HOSTS.test(new URL(r.url).hostname))
    .slice(0, MAX_ARTICLES);

  const articles = await Promise.all(
    picked.map(async (r) => {
      const page = await readPage(r.url, fetchImpl).catch(() => '');
      const text = prepareText(`${r.title} ${r.description ?? ''} ${page}`);
      const matches = names.flatMap((variants, i) => (mentions(text, variants) ? [i] : []));
      return { title: htmlToText(r.title).trim(), url: r.url, matches };
    }),
  );
  return json({ articles });
}
