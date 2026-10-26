import type { Strings } from '../i18n';
import type { Filters, SortKey } from '../types';

interface Props {
  filters: Filters;
  onChange(f: Filters): void;
  t: Strings;
}

const RADII = [500, 1000, 2000, 5000];

export function FilterBar({ filters, onChange, t }: Props) {
  const set = <K extends keyof Filters>(k: K, v: Filters[K]) => onChange({ ...filters, [k]: v });
  return (
    <div className="filters">
      <label>
        {t.minRating}
        <select value={filters.minRating} onChange={(e) => set('minRating', Number(e.target.value))}>
          <option value={0}>{t.any}</option>
          {[3.5, 4, 4.5].map((r) => (
            <option key={r} value={r}>
              {r}+ ★
            </option>
          ))}
        </select>
      </label>
      <label>
        {t.maxPrice}
        <select value={filters.maxPrice} onChange={(e) => set('maxPrice', Number(e.target.value))}>
          <option value={4}>{t.any}</option>
          {[1, 2, 3].map((p) => (
            <option key={p} value={p}>
              {'$'.repeat(p)}
            </option>
          ))}
        </select>
      </label>
      <label>
        {t.radius}
        <select value={filters.radius} onChange={(e) => set('radius', Number(e.target.value))}>
          {RADII.map((r) => (
            <option key={r} value={r}>
              {r < 1000 ? `${r} m` : `${r / 1000} km`}
            </option>
          ))}
        </select>
      </label>
      <label>
        {t.sortBy}
        <select value={filters.sort} onChange={(e) => set('sort', e.target.value as SortKey)}>
          <option value="distance">{t.sortDistance}</option>
          <option value="rating">{t.sortRating}</option>
        </select>
      </label>
      <label className="check">
        <input type="checkbox" checked={filters.openNow} onChange={(e) => set('openNow', e.target.checked)} />
        {t.openNow}
      </label>
    </div>
  );
}
