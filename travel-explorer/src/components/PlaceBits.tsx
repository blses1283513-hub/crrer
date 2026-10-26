import { CATEGORY_BY_ID } from '../categories';
import type { Strings } from '../i18n';
import type { Place } from '../types';

export function Thumb({ place, size }: { place: Place; size: number }) {
  const cat = CATEGORY_BY_ID[place.category];
  const photo = place.photos?.[0];
  return (
    <div className="thumb" style={{ width: size, height: size, background: cat.color }}>
      <span aria-hidden>{cat.emoji}</span>
      {photo && (
        <img
          src={photo.url}
          alt=""
          loading="lazy"
          onError={(e) => (e.currentTarget.style.display = 'none')}
        />
      )}
    </div>
  );
}

export function Meta({ place, t }: { place: Place; t: Strings }) {
  return (
    <div className="meta">
      {place.rating !== undefined && (
        <span className="rating">
          ★ {place.rating.toFixed(1)}
          {place.ratingCount !== undefined && <span className="muted"> ({place.ratingCount.toLocaleString()})</span>}
        </span>
      )}
      {place.priceLevel !== undefined && place.priceLevel > 0 && <span>{'$'.repeat(place.priceLevel)}</span>}
      {place.openNow !== undefined && (
        <span className={place.openNow ? 'badge badge--open' : 'badge badge--closed'}>
          {place.openNow ? t.openNow : t.closed}
        </span>
      )}
    </div>
  );
}

export function HeartButton({ saved, onClick, t }: { saved: boolean; onClick(): void; t: Strings }) {
  return (
    <button
      className={saved ? 'heart heart--on' : 'heart'}
      aria-pressed={saved}
      aria-label={saved ? t.unsave : t.save}
      title={saved ? t.unsave : t.save}
      onClick={(e) => {
        e.stopPropagation();
        onClick();
      }}
    >
      {saved ? '♥' : '♡'}
    </button>
  );
}
