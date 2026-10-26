import { CATEGORY_BY_ID } from '../categories';
import type { Backend, CategoryId, LatLng, Place } from '../types';

type PlacesLib = google.maps.PlacesLibrary;

// Every field requested here is billed, so keep the list to what the UI shows.
const FIELDS = [
  'id',
  'displayName',
  'location',
  'formattedAddress',
  'rating',
  'userRatingCount',
  'priceLevel',
  'photos',
  'googleMapsURI',
  'regularOpeningHours',
  'utcOffsetMinutes',
  'businessStatus',
];

const PRICE_LEVELS = ['FREE', 'INEXPENSIVE', 'MODERATE', 'EXPENSIVE', 'VERY_EXPENSIVE'];

async function toPlace(p: google.maps.places.Place, category: CategoryId): Promise<Place | null> {
  if (!p.location || p.businessStatus === 'CLOSED_PERMANENTLY') return null;
  let openNow: boolean | undefined;
  if (p.regularOpeningHours) {
    try {
      openNow = (await p.isOpen()) ?? undefined;
    } catch {
      openNow = undefined;
    }
  }
  const price = p.priceLevel ? PRICE_LEVELS.indexOf(String(p.priceLevel)) : -1;
  return {
    id: p.id,
    name: p.displayName ?? '',
    category,
    location: p.location.toJSON(),
    address: p.formattedAddress ?? undefined,
    rating: p.rating ?? undefined,
    ratingCount: p.userRatingCount ?? undefined,
    priceLevel: price >= 0 ? price : undefined,
    openNow,
    hours: p.regularOpeningHours?.weekdayDescriptions,
    photos: p.photos?.slice(0, 4).map((ph) => ({
      url: ph.getURI({ maxWidth: 800 }),
      author: ph.authorAttributions[0]?.displayName,
      authorUrl: ph.authorAttributions[0]?.uri ?? undefined,
    })),
    mapsUrl: p.googleMapsURI ?? undefined,
    isGooglePlace: true,
  };
}

export function createGoogleBackend(lib: PlacesLib | null): Backend {
  return {
    kind: 'google',
    ready: lib !== null,

    async search(center: LatLng, radius: number, categoryId: CategoryId, lang) {
      if (!lib) return [];
      const cat = CATEGORY_BY_ID[categoryId];
      const requests: Promise<{ places: google.maps.places.Place[] }>[] = [
        lib.Place.searchNearby({
          fields: FIELDS,
          includedTypes: cat.types,
          locationRestriction: { center, radius },
          maxResultCount: 20,
          rankPreference: lib.SearchNearbyRankPreference.POPULARITY,
          language: lang,
        }),
      ];
      if (cat.textQuery) {
        requests.push(
          lib.Place.searchByText({
            textQuery: cat.textQuery,
            fields: FIELDS,
            locationBias: { center, radius },
            maxResultCount: 20,
            language: lang,
          }),
        );
      }
      const responses = await Promise.all(requests);
      const places = await Promise.all(responses.flatMap((r) => r.places).map((p) => toPlace(p, categoryId)));
      return places.filter((p): p is Place => p !== null);
    },

    async findArea(query, lang) {
      if (!lib) return null;
      const { places } = await lib.Place.searchByText({
        textQuery: query,
        fields: ['location'],
        maxResultCount: 1,
        language: lang,
      });
      return places[0]?.location?.toJSON() ?? null;
    },
  };
}
