import type { Level, Place, PlaceSignals, Ranking, SignalAvailability } from '../types';

export const WEIGHTS = { quality: 0.3, volume: 0.2, video: 0.25, articles: 0.25 };

const clamp = (x: number) => Math.max(0, Math.min(1, x));

/** Star rating pulled toward 4.0 when there are few reviews (Bayesian average), mapped 3.5★→0 … 5★→1. */
export function qualityScore(rating?: number, count = 0): number {
  if (rating === undefined) return 0;
  const m = 50;
  const prior = 4.0;
  const adjusted = (count * rating + m * prior) / (count + m);
  return clamp((adjusted - 3.5) / 1.5);
}

/** Review volume on a log scale: 10 reviews → 0.26, 1,000 → 0.75, 10,000+ → 1. */
export function volumeScore(count = 0): number {
  return clamp(Math.log10(count + 1) / 4);
}

/** Total views (log scale, 10M → 1) weighted 70%, number of distinct videos (5+ → 1) weighted 30%. */
export function videoScore(s: PlaceSignals): number {
  if (s.videos.length === 0) return 0;
  const views = s.videos.reduce((sum, v) => sum + v.views, 0);
  return 0.7 * clamp(Math.log10(views + 1) / 7) + 0.3 * clamp(s.videos.length / 5);
}

/** Wikivoyage listing (40%) + number of blog articles mentioning it (3+ → full, 60%), over whichever is available. */
export function articleScore(s: PlaceSignals, available: SignalAvailability): number | undefined {
  let sum = 0;
  let weight = 0;
  if (available.wikivoyage) {
    sum += 0.4 * (s.wikivoyage ? 1 : 0);
    weight += 0.4;
  }
  if (available.articles) {
    sum += 0.6 * clamp(s.articles.length / 3);
    weight += 0.6;
  }
  return weight ? sum / weight : undefined;
}

export function levelFor(score: number, offMapSources: number): Level {
  if (score >= 80) return offMapSources >= 2 ? 'S' : 'A'; // S needs proof beyond the map
  if (score >= 65) return 'A';
  if (score >= 45) return 'B';
  return 'C';
}

export function computeRanking(
  place: Place,
  signals: PlaceSignals,
  available: SignalAvailability,
  sample = false,
): Ranking {
  const quality = qualityScore(place.rating, place.ratingCount);
  const volume = volumeScore(place.ratingCount);
  const video = available.video ? videoScore(signals) : undefined;
  const articles = articleScore(signals, available);

  // Unavailable signals (no key, quota used up, server down) are left out rather than counted as zero.
  let sum = WEIGHTS.quality * quality + WEIGHTS.volume * volume;
  let weight = WEIGHTS.quality + WEIGHTS.volume;
  if (video !== undefined) {
    sum += WEIGHTS.video * video;
    weight += WEIGHTS.video;
  }
  if (articles !== undefined) {
    sum += WEIGHTS.articles * articles;
    weight += WEIGHTS.articles;
  }
  const score = Math.round((100 * sum) / weight);
  const offMapSources =
    (signals.videos.length > 0 ? 1 : 0) + (signals.wikivoyage ? 1 : 0) + (signals.articles.length > 0 ? 1 : 0);

  return {
    score,
    level: levelFor(score, offMapSources),
    parts: { quality, volume, video, articles },
    offMapSources,
    signals,
    sample: sample || undefined,
  };
}

const LEVEL_RANK: Record<Level, number> = { S: 0, A: 1, B: 2, C: 3 };

export function compareRecommended(a: Place, b: Place): number {
  const la = a.ranking ? LEVEL_RANK[a.ranking.level] : 4;
  const lb = b.ranking ? LEVEL_RANK[b.ranking.level] : 4;
  return la - lb || (b.ranking?.score ?? 0) - (a.ranking?.score ?? 0);
}
