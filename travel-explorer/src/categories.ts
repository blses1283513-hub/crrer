import type { CategoryId } from './types';

export interface Category {
  id: CategoryId;
  emoji: string;
  color: string;
  /** Google Places (New) Table A types used for Nearby Search */
  types: string[];
  /** Extra Text Search query, for things that have no searchable place type */
  textQuery?: string;
}

// Type names checked against https://developers.google.com/maps/documentation/places/web-service/place-types
// (only types usable in requests; e.g. `scenic_spot` is response-only, hence the text query for photo spots).
export const CATEGORIES: Category[] = [
  { id: 'restaurant', emoji: '🍜', color: '#e11d48', types: ['restaurant'] },
  { id: 'cafe', emoji: '☕', color: '#a16207', types: ['cafe', 'coffee_shop', 'bakery'] },
  { id: 'bar', emoji: '🍸', color: '#7c3aed', types: ['bar', 'pub', 'wine_bar'] },
  {
    id: 'attractions',
    emoji: '🏛️',
    color: '#2563eb',
    types: ['tourist_attraction', 'museum', 'historical_landmark', 'art_gallery'],
  },
  {
    id: 'nature',
    emoji: '🌿',
    color: '#16a34a',
    types: ['park', 'national_park', 'hiking_area', 'beach', 'botanical_garden'],
  },
  { id: 'photo', emoji: '📸', color: '#db2777', types: ['observation_deck'], textQuery: 'scenic viewpoint' },
  {
    id: 'entertainment',
    emoji: '🎡',
    color: '#ea580c',
    types: ['amusement_park', 'night_club', 'movie_theater', 'karaoke', 'bowling_alley', 'aquarium', 'zoo'],
  },
  { id: 'shopping', emoji: '🛍️', color: '#0891b2', types: ['shopping_mall', 'market'] },
];

export const CATEGORY_BY_ID = Object.fromEntries(CATEGORIES.map((c) => [c.id, c])) as Record<
  CategoryId,
  Category
>;
