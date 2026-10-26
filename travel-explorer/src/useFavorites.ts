import { useCallback, useState } from 'react';
import type { Place } from './types';

const KEY = 'travel-explorer:favorites';

function load(): Place[] {
  try {
    const raw = localStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as Place[]) : [];
  } catch {
    return [];
  }
}

/** Saved places, kept in this browser only. */
export function useFavorites() {
  const [favorites, setFavorites] = useState<Place[]>(load);

  const toggle = useCallback((place: Place) => {
    setFavorites((prev) => {
      const next = prev.some((p) => p.id === place.id) ? prev.filter((p) => p.id !== place.id) : [...prev, place];
      try {
        localStorage.setItem(KEY, JSON.stringify(next));
      } catch {
        // storage unavailable (private mode etc.): keep in memory only
      }
      return next;
    });
  }, []);

  const isSaved = useCallback((id: string) => favorites.some((p) => p.id === id), [favorites]);

  return { favorites, toggle, isSaved };
}
