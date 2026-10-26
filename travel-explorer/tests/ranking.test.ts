import { describe, expect, it } from 'vitest';
import { mentions, nameVariants, prepareText } from '../src/ranking/match';
import { buildQuery, localLangFor, rankingLangs } from '../src/ranking/queries';
import { articleScore, compareRecommended, computeRanking, levelFor, qualityScore, videoScore, volumeScore } from '../src/ranking/score';
import type { Place, PlaceSignals, SignalAvailability } from '../src/types';

const ALL: SignalAvailability = { video: true, articles: true, wikivoyage: true };
const place = (rating?: number, ratingCount?: number): Place => ({
  id: 'p', name: 'X', category: 'cafe', location: { lat: 0, lng: 0 }, rating, ratingCount,
});
const videos = (n: number, totalViews: number) =>
  Array.from({ length: n }, (_, i) => ({ id: `v${i}`, title: '', channel: '', url: '', views: totalViews / n }));

describe('score parts', () => {
  it('pulls ratings with few reviews toward 4.0', () => {
    expect(qualityScore(5, 3)).toBeLessThan(qualityScore(4.6, 5000));
    expect(qualityScore(undefined)).toBe(0);
    expect(qualityScore(5, 1e6)).toBeCloseTo(1, 2);
  });
  it('scores review volume on a log scale', () => {
    expect(volumeScore(0)).toBe(0);
    expect(volumeScore(999)).toBeCloseTo(0.75, 2);
    expect(volumeScore(1e6)).toBe(1);
  });
  it('rewards views and number of videos', () => {
    expect(videoScore({ videos: [], articles: [] })).toBe(0);
    expect(videoScore({ videos: videos(5, 1e7), articles: [] })).toBeCloseTo(1, 2);
    expect(videoScore({ videos: videos(1, 1e4), articles: [] })).toBeLessThan(videoScore({ videos: videos(3, 1e6), articles: [] }));
  });
  it('re-weights articles when a source is unavailable', () => {
    const s: PlaceSignals = { videos: [], articles: [], wikivoyage: { title: 'Kyoto', url: '' } };
    expect(articleScore(s, ALL)).toBeCloseTo(0.4);
    expect(articleScore(s, { ...ALL, articles: false })).toBe(1);
    expect(articleScore(s, { video: true, articles: false, wikivoyage: false })).toBeUndefined();
  });
});

describe('levels', () => {
  it('uses the proposed thresholds', () => {
    expect(levelFor(90, 2)).toBe('S');
    expect(levelFor(79, 3)).toBe('A');
    expect(levelFor(65, 0)).toBe('A');
    expect(levelFor(64, 0)).toBe('B');
    expect(levelFor(45, 0)).toBe('B');
    expect(levelFor(44, 3)).toBe('C');
  });
  it('never gives S on map reviews alone', () => {
    expect(levelFor(95, 1)).toBe('A');
    const r = computeRanking(place(4.9, 50000), { videos: [], articles: [] }, { video: false, articles: false, wikivoyage: false });
    expect(r.score).toBeGreaterThanOrEqual(80);
    expect(r.level).toBe('A');
  });
  it('makes a famous, well-covered landmark S and an unknown spot C', () => {
    const famous = computeRanking(
      place(4.6, 6000),
      { videos: videos(30, 9e6), articles: [{ title: '', url: 'a' }, { title: '', url: 'b' }, { title: '', url: 'c' }], wikivoyage: { title: 'K', url: '' } },
      ALL,
    );
    expect(famous.level).toBe('S');
    expect(famous.offMapSources).toBe(3);
    const unknown = computeRanking(place(4.3, 560), { videos: [], articles: [] }, ALL);
    expect(unknown.level).toBe('C');
  });
  it('sorts by level, then score', () => {
    const mk = (id: string, level: 'S' | 'A' | 'B' | 'C', score: number): Place => ({
      ...place(), id, ranking: { level, score, parts: { quality: 0, volume: 0 }, offMapSources: 0, signals: { videos: [], articles: [] } },
    });
    const sorted = [mk('b1', 'B', 50), mk('s', 'S', 85), mk('a', 'A', 70), mk('b2', 'B', 60), place()].sort(compareRecommended);
    expect(sorted.map((p) => p.id)).toEqual(['s', 'a', 'b2', 'b1', 'p']);
  });
});

describe('name matching', () => {
  it('builds variants from parentheses, hyphens and other languages', () => {
    const v = nameVariants(['Yasaka Pagoda (Hokan-ji)', '八坂塔（法觀寺）']);
    expect(v).toEqual(expect.arrayContaining(['yasaka pagoda', 'hokan ji', 'hokanji', '八坂塔', '法觀寺']));
  });
  it('matches whole words for Latin names and substrings for CJK', () => {
    const text = prepareText('Top 10: Kiyomizudera, Nishiki Market and 八坂神社に行ってきた!');
    expect(mentions(text, nameVariants(['Kiyomizu-dera']))).toBe(true);
    expect(mentions(text, nameVariants(['Nishiki Market']))).toBe(true);
    expect(mentions(text, nameVariants(['八坂神社']))).toBe(true);
    expect(mentions(text, nameVariants(['Nishi']))).toBe(false); // not a whole word
  });
  it('ignores names that are too generic', () => {
    expect(nameVariants(['Park', 'Cafe', 'Bar'])).toEqual([]);
    expect(mentions(prepareText('a nice park nearby'), nameVariants(['Park']))).toBe(false);
  });
});

describe('queries', () => {
  it('searches English, Chinese and the local language without duplicates', () => {
    expect(rankingLangs('HK')).toEqual(['en', 'zh-TW', 'zh-HK']);
    expect(rankingLangs('JP')).toEqual(['en', 'zh-TW', 'ja']);
    expect(rankingLangs('TW')).toEqual(['en', 'zh-TW']);
    expect(rankingLangs('US')).toEqual(['en', 'zh-TW']);
    expect(localLangFor(undefined)).toBeUndefined();
  });
  it('phrases queries the way locals search', () => {
    expect(buildQuery('en', 'cafe', 'Kyoto')).toBe('best cafes in Kyoto');
    expect(buildQuery('zh-TW', 'cafe', '京都')).toBe('京都 咖啡廳 推薦');
    expect(buildQuery('zh-HK', 'attractions', '香港')).toBe('香港 好去處 推介');
    expect(buildQuery('ja', 'cafe', '京都市')).toBe('京都市 カフェ おすすめ');
  });
});
