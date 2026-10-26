export type LatLng = { lat: number; lng: number };

export type CategoryId =
  | 'restaurant'
  | 'cafe'
  | 'bar'
  | 'attractions'
  | 'nature'
  | 'photo'
  | 'entertainment'
  | 'shopping';

/** UI languages */
export type Lang = 'en' | 'zh-TW';

/** Languages used for place names and online-buzz queries (UI languages + destination languages). */
export type QueryLang = Lang | 'zh-HK' | 'zh-CN' | 'ja' | 'ko' | 'th' | 'fr' | 'es' | 'de' | 'it';

export type Level = 'S' | 'A' | 'B' | 'C';

export interface VideoEvidence {
  id: string;
  title: string;
  channel: string;
  views: number;
  url: string;
}

export interface ArticleEvidence {
  title: string;
  url: string;
}

/** What the outside world says about a place, beyond the map. */
export interface PlaceSignals {
  videos: VideoEvidence[];
  articles: ArticleEvidence[];
  wikivoyage?: ArticleEvidence;
}

export interface SignalAvailability {
  video: boolean;
  articles: boolean;
  wikivoyage: boolean;
}

export interface Ranking {
  /** 0–100 */
  score: number;
  level: Level;
  /** each 0–1, before weighting; undefined when that signal was unavailable */
  parts: { quality: number; volume: number; video?: number; articles?: number };
  /** how many non-map sources mention the place (videos, Wikivoyage, blog articles) */
  offMapSources: number;
  signals: PlaceSignals;
  /** true for made-up demo numbers */
  sample?: boolean;
}

export interface PlacePhoto {
  url: string;
  author?: string;
  authorUrl?: string;
}

export interface Place {
  id: string;
  name: string;
  category: CategoryId;
  location: LatLng;
  address?: string;
  rating?: number;
  ratingCount?: number;
  /** 0 = free … 4 = very expensive */
  priceLevel?: number;
  openNow?: boolean;
  hours?: string[];
  photos?: PlacePhoto[];
  mapsUrl?: string;
  /** true when the id is a real Google place id (enables place-aware directions links) */
  isGooglePlace?: boolean;
  /** the place's name in other languages, used to spot it in videos and articles */
  names?: Partial<Record<QueryLang, string>>;
  /** ISO country code and city name, used to build "best X in <city>" queries */
  countryCode?: string;
  city?: string;
  ranking?: Ranking;
}

export type SortKey = 'recommended' | 'distance' | 'rating';

export interface Filters {
  minRating: number;
  /** highest allowed price level; 4 = no limit */
  maxPrice: number;
  openNow: boolean;
  /** search radius in meters */
  radius: number;
  sort: SortKey;
}

export interface FlyTo {
  center: LatLng;
  zoom?: number;
  /** changes on every request so the same target can be flown to twice */
  nonce: number;
}

export interface SearchOptions {
  /** only fetch ids, names and address (cheaper); used to learn names in other languages */
  namesOnly?: boolean;
}

/** Where place data comes from: Google Places, or bundled sample data. */
export interface Backend {
  kind: 'google' | 'demo';
  ready: boolean;
  search(center: LatLng, radius: number, category: CategoryId, lang: QueryLang, opts?: SearchOptions): Promise<Place[]>;
  /** Look up a city / area name. Undefined when the backend can't geocode. */
  findArea?(query: string, lang: Lang): Promise<LatLng | null>;
}

export interface RankContext {
  /** query languages, e.g. ['en', 'zh-TW', 'ja'] */
  langs: QueryLang[];
  /** city name per language (falls back to English) */
  cityByLang: Partial<Record<QueryLang, string>>;
  countryCode?: string;
  categories: CategoryId[];
}

export interface SignalReport {
  byId: Map<string, PlaceSignals>;
  available: SignalAvailability;
  /** human-readable notes, e.g. "YouTube daily quota used up" */
  notes: string[];
}

/** Collects off-map evidence (videos, articles, guides) for a batch of places. */
export interface SignalProvider {
  kind: 'live' | 'demo';
  collect(places: Place[], ctx: RankContext): Promise<SignalReport>;
}

export interface MapViewProps {
  initialCenter: LatLng;
  flyTo?: FlyTo;
  places: Place[];
  selectedId?: string;
  userLocation?: LatLng;
  onSelect(id: string): void;
  onCenterChange(center: LatLng): void;
}
