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

export type Lang = 'en' | 'zh-TW';

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
}

export type SortKey = 'distance' | 'rating';

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

/** Where place data comes from: Google Places, or bundled sample data. */
export interface Backend {
  kind: 'google' | 'demo';
  ready: boolean;
  search(center: LatLng, radius: number, category: CategoryId, lang: Lang): Promise<Place[]>;
  /** Look up a city / area name. Undefined when the backend can't geocode. */
  findArea?(query: string, lang: Lang): Promise<LatLng | null>;
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
