// Fuzzy-but-careful detection of a place's name inside video descriptions and articles.
// Shared by the browser (YouTube) and the server (blog articles).

const CJK = /[\p{Script=Han}\p{Script=Hiragana}\p{Script=Katakana}\p{Script=Hangul}\p{Script=Thai}]/u;

// Names that are too generic to count as a mention on their own.
const GENERIC = new Set([
  'park', 'parks', 'museum', 'cafe', 'coffee', 'bakery', 'restaurant', 'bar', 'pub', 'market', 'temple', 'shrine',
  'beach', 'garden', 'tower', 'station', 'mall', 'cinema', 'karaoke', 'river', 'lake', 'hotel', 'the bar', 'the cafe',
]);

export function normalize(s: string): string {
  return s
    .normalize('NFKC')
    .toLowerCase()
    .replace(/['’`]/g, '')
    .replace(/[^\p{L}\p{N}]+/gu, ' ')
    .trim();
}

function useful(n: string): boolean {
  if (!n) return false;
  if (CJK.test(n)) return n.replace(/\s/g, '').length >= 2;
  return n.length >= 4 && !GENERIC.has(n);
}

/**
 * Turn a place's names (in any languages) into normalized search variants:
 * "Yasaka Pagoda (Hokan-ji)" → ["yasaka pagoda hokan ji", "yasaka pagoda", "hokan ji", "hokanji", …]
 */
export function nameVariants(names: (string | undefined)[]): string[] {
  const out = new Set<string>();
  for (const raw of names) {
    if (!raw) continue;
    const inner = [...raw.matchAll(/[（(]([^）)]+)[）)]/g)].map((m) => m[1]);
    const outer = raw.replace(/\s*[（(][^）)]*[）)]\s*/g, ' ');
    for (const piece of [raw, outer, ...inner, ...outer.split(/\s+[&|/–-]\s+/)]) {
      for (const v of [piece, piece.replace(/-/g, '')]) {
        const n = normalize(v);
        if (useful(n)) out.add(n);
      }
    }
  }
  return [...out];
}

export interface PreparedText {
  spaced: string;
  compact: string;
}

export function prepareText(text: string): PreparedText {
  const n = normalize(text);
  return { spaced: ` ${n} `, compact: n.replace(/ /g, '') };
}

/** Latin names must match on word boundaries; CJK/Thai names match anywhere (no spaces in those scripts). */
export function mentions(text: PreparedText, variants: string[]): boolean {
  return variants.some((v) => (CJK.test(v) ? text.compact.includes(v.replace(/ /g, '')) : text.spaced.includes(` ${v} `)));
}
