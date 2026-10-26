import { Fragment } from 'react';
import { formatDistance } from '../geo';
import type { Strings } from '../i18n';
import type { Lang, Place } from '../types';
import { BuzzLine, HeartButton, LevelBadge, Meta, Thumb } from './PlaceBits';

interface Props {
  places: (Place & { distance: number })[];
  /** show S / A / B / C section headers (list must be sorted by level) */
  grouped: boolean;
  selectedId?: string;
  isSaved(id: string): boolean;
  onSelect(id: string): void;
  onToggleSave(p: Place): void;
  lang: Lang;
  t: Strings;
}

export function PlaceList({ places, grouped, selectedId, isSaved, onSelect, onToggleSave, lang, t }: Props) {
  return (
    <ul className="list">
      {places.map((p, i) => {
        const level = p.ranking?.level;
        const header = grouped && level && level !== places[i - 1]?.ranking?.level;
        return (
          <Fragment key={p.id}>
            {header && (
              <li className="group" aria-hidden>
                <LevelBadge level={level} t={t} withLabel />
              </li>
            )}
            <li>
              <div
                role="button"
                tabIndex={0}
                className={p.id === selectedId ? 'row row--selected' : 'row'}
                onClick={() => onSelect(p.id)}
                onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && onSelect(p.id)}
              >
                <Thumb place={p} size={64} />
                <div className="row-body">
                  <div className="row-title">
                    {level && <LevelBadge level={level} t={t} />} {p.name}
                  </div>
                  <Meta place={p} t={t} />
                  <BuzzLine place={p} lang={lang} t={t} />
                  <div className="muted small">
                    {t.categories[p.category]} · {formatDistance(p.distance)} {t.away}
                  </div>
                </div>
                <HeartButton saved={isSaved(p.id)} onClick={() => onToggleSave(p)} t={t} />
              </div>
            </li>
          </Fragment>
        );
      })}
    </ul>
  );
}
