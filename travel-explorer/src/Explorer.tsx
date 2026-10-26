import { type ComponentType, type FormEvent, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { CATEGORIES } from './categories';
import { FilterBar } from './components/FilterBar';
import { PlaceDetail } from './components/PlaceDetail';
import { PlaceList } from './components/PlaceList';
import { distanceMeters } from './geo';
import { STRINGS } from './i18n';
import { rankingLangs } from './ranking/queries';
import { mostCommon, rankPlaces } from './ranking/rank';
import { compareRecommended } from './ranking/score';
import type {
  Backend,
  CategoryId,
  Filters,
  FlyTo,
  Lang,
  LatLng,
  MapViewProps,
  Place,
  QueryLang,
  SignalProvider,
} from './types';
import { useFavorites } from './useFavorites';

interface Props {
  backend: Backend;
  signals: SignalProvider;
  MapView: ComponentType<MapViewProps>;
  initialCenter: LatLng;
  lang: Lang;
  onLangChange(l: Lang): void;
}

const DEFAULT_FILTERS: Filters = { minRating: 0, maxPrice: 4, openNow: false, radius: 2000, sort: 'recommended' };
const DEFAULT_CATEGORIES: CategoryId[] = ['restaurant', 'cafe', 'attractions'];

export function Explorer({ backend, signals, MapView, initialCenter, lang, onLangChange }: Props) {
  const t = STRINGS[lang];
  const [cats, setCats] = useState<Set<CategoryId>>(() => new Set(DEFAULT_CATEGORIES));
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [searchCenter, setSearchCenter] = useState<LatLng>(initialCenter);
  const [viewCenter, setViewCenter] = useState<LatLng>(initialCenter);
  const [results, setResults] = useState<Place[]>([]);
  const [phase, setPhase] = useState<'places' | 'ranking'>();
  const [error, setError] = useState<string>();
  const [notes, setNotes] = useState<string[]>([]);
  const [tab, setTab] = useState<'results' | 'saved'>('results');
  const [selectedId, setSelectedId] = useState<string>();
  const [flyTo, setFlyTo] = useState<FlyTo>();
  const [userLocation, setUserLocation] = useState<LatLng>();
  const [query, setQuery] = useState('');
  const { favorites, toggle, isSaved } = useFavorites();
  const requestId = useRef(0);
  const panelRef = useRef<HTMLElement>(null);

  const fly = (center: LatLng, zoom?: number) => setFlyTo({ center, zoom, nonce: Date.now() });

  const runSearch = useCallback(
    async (center: LatLng) => {
      setSearchCenter(center);
      if (!backend.ready) return;
      const id = ++requestId.current;
      const stale = () => id !== requestId.current; // a newer search started meanwhile
      setError(undefined);
      setNotes([]);
      if (cats.size === 0) {
        setResults([]);
        return;
      }
      const catList = [...cats];

      // 1. Find candidate places on the map.
      setPhase('places');
      const settled = await Promise.allSettled(catList.map((c) => backend.search(center, filters.radius, c, lang)));
      if (stale()) return;
      const seen = new Set<string>();
      const found: Place[] = [];
      for (const r of settled) {
        if (r.status !== 'fulfilled') continue;
        for (const p of r.value) {
          if (!seen.has(p.id)) {
            seen.add(p.id);
            found.push(p);
          }
        }
      }
      const failure = settled.find((r): r is PromiseRejectedResult => r.status === 'rejected');
      if (failure) setError(`${t.searchFailed}: ${String(failure.reason?.message ?? failure.reason)}`);
      if (found.length === 0) {
        setResults([]);
        setPhase(undefined);
        return;
      }

      // 2. Learn each place's name in English, Chinese and the local language, so we can spot it online.
      setPhase('ranking');
      const countryCode = mostCommon(found.map((p) => p.countryCode));
      const langs = rankingLangs(countryCode);
      const cityByLang: Partial<Record<QueryLang, string>> = { [lang]: mostCommon(found.map((p) => p.city)) };
      const names = new Map(found.map((p) => [p.id, { ...p.names, [lang]: p.name } as Partial<Record<QueryLang, string>>]));
      await Promise.all(
        langs
          .filter((l) => l !== lang)
          .map(async (l) => {
            const res = await Promise.allSettled(
              catList.map((c) => backend.search(center, filters.radius, c, l, { namesOnly: true })),
            );
            const localized = res.flatMap((r) => (r.status === 'fulfilled' ? r.value : []));
            cityByLang[l] = mostCommon(localized.map((p) => p.city));
            for (const p of localized) {
              const n = names.get(p.id);
              if (n && !n[l]) n[l] = p.name;
            }
          }),
      );
      if (stale()) return;
      const withNames = found.map((p) => ({ ...p, names: names.get(p.id) }));

      // 3. Rank with videos, articles and travel guides before showing anything.
      try {
        const ranked = await rankPlaces(withNames, signals, { langs, cityByLang, countryCode, categories: catList });
        if (stale()) return;
        setResults(ranked.places);
        setNotes(ranked.report.notes);
      } catch (e) {
        if (stale()) return;
        setResults(withNames);
        setNotes([String((e as Error).message ?? e)]);
      }
      setPhase(undefined);
    },
    [backend, signals, cats, filters.radius, lang, t.searchFailed],
  );

  // Re-search whenever the inputs that change the query change.
  useEffect(() => {
    runSearch(searchCenter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runSearch]);

  const locate = useCallback(
    (quiet: boolean) => {
      if (!navigator.geolocation) return;
      navigator.geolocation.getCurrentPosition(
        (pos) => {
          const here = { lat: pos.coords.latitude, lng: pos.coords.longitude };
          setUserLocation(here);
          fly(here, 15);
          runSearch(here);
        },
        (err) => !quiet && setError(err.message),
        { enableHighAccuracy: true, timeout: 10000 },
      );
    },
    [runSearch],
  );

  // With real data, start where the traveller is. Demo data only covers Kyoto, so skip it there.
  useEffect(() => {
    if (backend.kind === 'google' && backend.ready) locate(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [backend.kind, backend.ready]);

  const onSearchArea = async (e: FormEvent) => {
    e.preventDefault();
    if (!backend.findArea || !query.trim()) return;
    try {
      const center = await backend.findArea(query.trim(), lang);
      if (!center) return setError(t.areaNotFound);
      setSelectedId(undefined);
      setTab('results');
      fly(center, 14);
      runSearch(center);
    } catch (err) {
      setError(`${t.searchFailed}: ${String((err as Error).message ?? err)}`);
    }
  };

  const toggleCat = (id: CategoryId) =>
    setCats((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const origin = tab === 'results' ? searchCenter : viewCenter;
  const visible = useMemo(() => {
    const source =
      tab === 'saved'
        ? favorites
        : results.filter(
            (p) =>
              (p.rating ?? 0) >= filters.minRating &&
              (p.priceLevel === undefined || p.priceLevel <= filters.maxPrice) &&
              (!filters.openNow || p.openNow === true),
          );
    return source
      .map((p) => ({ ...p, distance: distanceMeters(origin, p.location) }))
      .sort((a, b) =>
        filters.sort === 'recommended'
          ? compareRecommended(a, b) || a.distance - b.distance
          : filters.sort === 'rating'
            ? (b.rating ?? 0) - (a.rating ?? 0)
            : a.distance - b.distance,
      );
  }, [tab, favorites, results, filters, origin]);

  const selected = visible.find((p) => p.id === selectedId) ?? results.concat(favorites).find((p) => p.id === selectedId);

  const select = (id: string, fromList: boolean) => {
    setSelectedId(id);
    const p = visible.find((v) => v.id === id);
    if (fromList && p) fly(p.location);
    panelRef.current?.scrollTo({ top: 0 });
  };

  const busy = phase !== undefined && tab === 'results';
  const showSearchArea = backend.ready && tab === 'results' && distanceMeters(viewCenter, searchCenter) > 300;

  useEffect(() => {
    document.documentElement.lang = lang;
    document.title = t.appTitle;
  }, [lang, t.appTitle]);

  return (
    <div className="app">
      <aside className="panel" ref={panelRef}>
        <header className="header">
          <h1>📍 {t.appTitle}</h1>
          <button className="lang" onClick={() => onLangChange(lang === 'en' ? 'zh-TW' : 'en')}>
            {lang === 'en' ? '中文' : 'EN'}
          </button>
        </header>

        {backend.kind === 'demo' && <div className="banner">{t.demoBanner}</div>}

        <form className="search" onSubmit={onSearchArea}>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={backend.findArea ? t.searchPlaceholder : t.searchDisabled}
            disabled={!backend.findArea}
            aria-label={t.searchPlaceholder}
          />
          <button className="btn btn--primary" disabled={!backend.findArea}>
            {t.go}
          </button>
        </form>

        <div className="chips" role="group">
          {CATEGORIES.map((c) => {
            const on = cats.has(c.id);
            return (
              <button
                key={c.id}
                className={on ? 'chip chip--on' : 'chip'}
                style={on ? { background: c.color, borderColor: c.color } : undefined}
                aria-pressed={on}
                onClick={() => toggleCat(c.id)}
              >
                {c.emoji} {t.categories[c.id]}
              </button>
            );
          })}
        </div>

        <details className="filters-box">
          <summary>{t.filters}</summary>
          <FilterBar filters={filters} onChange={setFilters} t={t} />
        </details>

        <div className="tabs" role="tablist">
          <button role="tab" aria-selected={tab === 'results'} onClick={() => setTab('results')}>
            {t.results} {tab === 'results' && !busy ? `(${visible.length})` : ''}
          </button>
          <button role="tab" aria-selected={tab === 'saved'} onClick={() => setTab('saved')}>
            ♥ {t.saved} ({favorites.length})
          </button>
        </div>

        {error && (
          <div className="error" role="alert">
            {error}
          </div>
        )}
        {notes.length > 0 && tab === 'results' && !busy && !selected && (
          <details className="notes">
            <summary>{t.sourcesNote}</summary>
            <ul>
              {notes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          </details>
        )}

        {selected ? (
          <PlaceDetail
            place={selected}
            distance={distanceMeters(origin, selected.location)}
            saved={isSaved(selected.id)}
            onBack={() => setSelectedId(undefined)}
            onToggleSave={() => toggle(selected)}
            lang={lang}
            t={t}
          />
        ) : busy ? (
          <p className="muted pad" role="status">
            {phase === 'ranking' ? t.ranking : t.loading}
          </p>
        ) : visible.length === 0 ? (
          <p className="muted pad">{tab === 'saved' ? t.noSaved : cats.size === 0 ? t.pickCategory : t.noResults}</p>
        ) : (
          <PlaceList
            places={visible}
            grouped={filters.sort === 'recommended'}
            selectedId={selectedId}
            isSaved={isSaved}
            onSelect={(id) => select(id, true)}
            onToggleSave={toggle}
            lang={lang}
            t={t}
          />
        )}
      </aside>

      <main className="map-wrap">
        <MapView
          initialCenter={initialCenter}
          flyTo={flyTo}
          places={busy ? [] : visible}
          selectedId={selectedId}
          userLocation={userLocation}
          onSelect={(id) => select(id, false)}
          onCenterChange={setViewCenter}
        />
        {showSearchArea && (
          <button className="float float--top" onClick={() => runSearch(viewCenter)}>
            🔍 {t.searchThisArea}
          </button>
        )}
        {backend.kind === 'google' && (
          <button className="float float--locate" onClick={() => locate(false)} title={t.locateMe} aria-label={t.locateMe}>
            ◎
          </button>
        )}
      </main>
    </div>
  );
}
