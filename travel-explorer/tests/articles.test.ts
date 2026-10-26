import { describe, expect, it, vi } from 'vitest';
import { handleArticles, htmlToText } from '../server/articles';

const post = (body: unknown, headers: Record<string, string> = {}) =>
  new Request('http://localhost/api/articles', { method: 'POST', headers: { 'Content-Type': 'application/json', ...headers }, body: JSON.stringify(body) });

const okBody = { q: 'best cafes in Kyoto', lang: 'en', names: [['kamogawa roasters'], ['matcha corner'], ['nowhere cafe']] };

function fakeFetch(pages: Record<string, string>, braveStatus = 200) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.startsWith('https://api.search.brave.com')) {
      if (braveStatus !== 200) return new Response('{}', { status: braveStatus });
      return Response.json({
        web: {
          results: [
            { title: 'Best cafes in Kyoto', url: 'https://blog.example.com/kyoto-cafes', description: 'Our picks' },
            { title: 'Video', url: 'https://www.youtube.com/watch?v=1', description: 'Kamogawa Roasters' },
            { title: 'Local IP', url: 'http://127.0.0.1/admin', description: 'Matcha Corner' },
            { title: 'Kyoto guide', url: 'https://travel.example.org/kyoto', description: 'Try Matcha Corner' },
          ],
        },
      });
    }
    const html = pages[url];
    return html === undefined
      ? new Response('nope', { status: 404 })
      : new Response(html, { headers: { 'content-type': 'text/html; charset=utf-8' } });
  }) as unknown as typeof fetch;
}

describe('POST /api/articles', () => {
  it('reports which places each article mentions, skipping videos and non-public hosts', async () => {
    const f = fakeFetch({
      'https://blog.example.com/kyoto-cafes': '<html><script>var x="Nowhere Cafe"</script><h2>1. Kamogawa&nbsp;Roasters</h2></html>',
      'https://travel.example.org/kyoto': '<p>Nothing here</p>',
    });
    const res = await handleArticles(post(okBody), { BRAVE_API_KEY: 'k' }, f);
    expect(res.status).toBe(200);
    const { articles } = await res.json();
    expect(articles).toEqual([
      { title: 'Best cafes in Kyoto', url: 'https://blog.example.com/kyoto-cafes', matches: [0] },
      { title: 'Kyoto guide', url: 'https://travel.example.org/kyoto', matches: [1] }, // matched via Brave's snippet
    ]);
    const fetched = (f as unknown as { mock: { calls: unknown[][] } }).mock.calls.map((c) => String(c[0]));
    expect(fetched.some((u) => u.includes('youtube.com') || u.includes('127.0.0.1'))).toBe(false);
    expect(fetched[0]).toContain('search_lang=en');
  });

  it('needs a key, valid input and an allowed origin', async () => {
    expect((await handleArticles(post(okBody), {}, fakeFetch({}))).status).toBe(503);
    expect((await handleArticles(post({ ...okBody, lang: 'xx' }), { BRAVE_API_KEY: 'k' }, fakeFetch({}))).status).toBe(400);
    expect((await handleArticles(post({ ...okBody, q: '' }), { BRAVE_API_KEY: 'k' }, fakeFetch({}))).status).toBe(400);
    const env = { BRAVE_API_KEY: 'k', ALLOWED_ORIGINS: 'https://mine.example' };
    expect((await handleArticles(post(okBody, { Origin: 'https://evil.example' }), env, fakeFetch({}))).status).toBe(403);
    expect((await handleArticles(post(okBody, { Origin: 'https://mine.example' }), env, fakeFetch({}))).status).toBe(200);
    expect((await handleArticles(new Request('http://localhost/api/articles'), { BRAVE_API_KEY: 'k' })).status).toBe(405);
  });

  it('passes Brave failures through as 502', async () => {
    expect((await handleArticles(post(okBody), { BRAVE_API_KEY: 'k' }, fakeFetch({}, 429))).status).toBe(502);
  });

  it('turns HTML into plain text', () => {
    expect(htmlToText('<style>p{}</style><p>Caf&#233; &amp; Bar</p>').trim()).toBe('Café & Bar');
  });
});
