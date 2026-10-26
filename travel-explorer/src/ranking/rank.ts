import type { Place, RankContext, SignalProvider, SignalReport } from '../types';
import { computeRanking } from './score';

const EMPTY = { videos: [], articles: [] };

/** Attach an S/A/B/C ranking to every place, using map reviews plus off-map evidence. */
export async function rankPlaces(
  places: Place[],
  provider: SignalProvider,
  ctx: RankContext,
): Promise<{ places: Place[]; report: SignalReport }> {
  const report = await provider.collect(places, ctx);
  return {
    report,
    places: places.map((p) => ({
      ...p,
      ranking: computeRanking(p, report.byId.get(p.id) ?? EMPTY, report.available, provider.kind === 'demo'),
    })),
  };
}

/** Most common non-empty value, e.g. the city most results are in. */
export function mostCommon<T>(values: (T | undefined)[]): T | undefined {
  const counts = new Map<T, number>();
  for (const v of values) if (v !== undefined && v !== '') counts.set(v, (counts.get(v) ?? 0) + 1);
  let best: T | undefined;
  let bestN = 0;
  for (const [v, n] of counts) if (n > bestN) [best, bestN] = [v, n];
  return best;
}
