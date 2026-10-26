import { CATEGORY_BY_ID } from '../categories';
import type { Strings } from '../i18n';
import type { Lang, Level, Place } from '../types';

export function compact(n: number, lang: Lang): string {
  return new Intl.NumberFormat(lang, { notation: 'compact', maximumFractionDigits: 1 }).format(n);
}

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

export function LevelBadge({ level, t, withLabel }: { level: Level; t: Strings; withLabel?: boolean }) {
  return (
    <span className={`lvl lvl--${level}`} title={t.levels[level]}>
      {level}
      {withLabel && <span className="lvl-label">· {t.levels[level]}</span>}
    </span>
  );
}

/** One-line summary of the off-map evidence: ▶ videos · 👁 views · 📰 articles · W guide */
export function BuzzLine({ place, lang, t }: { place: Place; lang: Lang; t: Strings }) {
  const s = place.ranking?.signals;
  if (!s || (!s.videos.length && !s.articles.length && !s.wikivoyage)) return null;
  const views = s.videos.reduce((sum, v) => sum + v.views, 0);
  return (
    <div className="buzz small">
      {s.videos.length > 0 && (
        <span title={t.partVideo}>
          ▶ {s.videos.length} · {compact(views, lang)} {t.views}
        </span>
      )}
      {s.articles.length > 0 && <span title={t.articlesHeading}>📰 {s.articles.length}</span>}
      {s.wikivoyage && <span title={t.wikivoyageListed}>🧭 Wikivoyage</span>}
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
