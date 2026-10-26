import { CATEGORY_BY_ID } from '../categories';
import { CITY_STATES } from '../ranking/queries';
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
  'addressComponents',
];

// Used to learn a place's name in another language (for spotting it in videos/articles).
const NAME_FIELDS = ['id', 'displayName', 'addressComponents'];

const PRICE_LEVELS = ['FREE', 'INEXPENSIVE', 'MODERATE', 'EXPENSIVE', 'VERY_EXPENSIVE'];

/** Country code and the city name to use in "best X in <city>" searches. */
function areaOf(p: google.maps.places.Place): { countryCode?: string; city?: string } {
  const comps = p.addressComponents ?? [];
  const find = (type: string) => comps.find((c) => c.types.includes(type));
  const country = find('country');
  const countryCode = country?.shortText ?? undefined;
  const city =
    countryCode && CITY_STATES.has(countryCode)
      ? country
      : (find('locality') ?? find('postal_town') ?? find('administrative_area_level_1') ?? country);
  return { countryCode, city: city?.longText ?? undefined };
}

function toNameOnly(p: google.maps.places.Place, category: CategoryId): Place {
  return { id: p.id, name: p.displayName ?? '', category, location: { lat: 0, lng: 0 }, ...areaOf(p) };
}

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
    ...areaOf(p),
  };
}

export function createGoogleBackend(lib: PlacesLib | null): Backend {
  return {
    kind: 'google',
    ready: lib !== null,

    async search(center: LatLng, radius: number, categoryId: CategoryId, lang, opts) {
      if (!lib) return [];
      const cat = CATEGORY_BY_ID[categoryId];
      const fields = opts?.namesOnly ? NAME_FIELDS : FIELDS;
      const requests: Promise<{ places: google.maps.places.Place[] }>[] = [
        lib.Place.searchNearby({
          fields,
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
            fields,
            locationBias: { center, radius },
            maxResultCount: 20,
            language: lang,
          }),
        );
      }
      const responses = await Promise.all(requests);
      if (opts?.namesOnly) return responses.flatMap((r) => r.places).map((p) => toNameOnly(p, categoryId));
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
