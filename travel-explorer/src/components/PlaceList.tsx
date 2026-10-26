import { formatDistance } from '../geo';
import type { Strings } from '../i18n';
import type { Place } from '../types';
import { HeartButton, Meta, Thumb } from './PlaceBits';

interface Props {
  places: (Place & { distance: number })[];
  selectedId?: string;
  isSaved(id: string): boolean;
  onSelect(id: string): void;
  onToggleSave(p: Place): void;
  t: Strings;
}

export function PlaceList({ places, selectedId, isSaved, onSelect, onToggleSave, t }: Props) {
  return (
    <ul className="list">
      {places.map((p) => (
        <li key={p.id}>
          <div
            role="button"
            tabIndex={0}
            className={p.id === selectedId ? 'row row--selected' : 'row'}
            onClick={() => onSelect(p.id)}
            onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelect(p.id)}
          >
            <Thumb place={p} size={64} />
            <div className="row-body">
              <div className="row-title">{p.name}</div>
              <Meta place={p} t={t} />
              <div className="muted small">
                {t.categories[p.category]} · {formatDistance(p.distance)} {t.away}
              </div>
            </div>
            <HeartButton saved={isSaved(p.id)} onClick={() => onToggleSave(p)} t={t} />
          </div>
        </li>
      ))}
    </ul>
  );
}
