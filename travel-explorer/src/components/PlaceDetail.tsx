import { CATEGORY_BY_ID } from '../categories';
import { formatDistance } from '../geo';
import type { Strings } from '../i18n';
import type { Lang, Place } from '../types';
import { BuzzLine, HeartButton, LevelBadge, Meta, Thumb } from './PlaceBits';
import { WhyLevel } from './WhyLevel';

interface Props {
  place: Place;
  distance: number;
  saved: boolean;
  onBack(): void;
  onToggleSave(): void;
  lang: Lang;
  t: Strings;
}

function directionsUrl(p: Place) {
  const u = new URL('https://www.google.com/maps/dir/');
  u.searchParams.set('api', '1');
  u.searchParams.set('destination', `${p.location.lat},${p.location.lng}`);
  if (p.isGooglePlace) u.searchParams.set('destination_place_id', p.id);
  return u.toString();
}

function mapsUrl(p: Place) {
  if (p.mapsUrl) return p.mapsUrl;
  const u = new URL('https://www.google.com/maps/search/');
  u.searchParams.set('api', '1');
  u.searchParams.set('query', p.name);
  return u.toString();
}

export function PlaceDetail({ place, distance, saved, onBack, onToggleSave, lang, t }: Props) {
  const cat = CATEGORY_BY_ID[place.category];
  return (
    <div className="detail">
      <div className="detail-top">
        <button className="link-btn" onClick={onBack}>
          ← {t.back}
        </button>
        <HeartButton saved={saved} onClick={onToggleSave} t={t} />
      </div>

      {place.photos?.length ? (
        <div className="photos">
          {place.photos.map((ph) => (
            <figure key={ph.url}>
              <img src={ph.url} alt={place.name} loading="lazy" />
              {ph.author && (
                <figcaption>
                  {t.photoBy}:{' '}
                  {ph.authorUrl ? (
                    <a href={ph.authorUrl} target="_blank" rel="noreferrer">
                      {ph.author}
                    </a>
                  ) : (
                    ph.author
                  )}
                </figcaption>
              )}
            </figure>
          ))}
        </div>
      ) : (
        <Thumb place={place} size={96} />
      )}

      <h2>
        {place.ranking && <LevelBadge level={place.ranking.level} t={t} />} {place.name}
      </h2>
      <div className="muted small">
        <span className="cat-dot" style={{ background: cat.color }} /> {t.categories[place.category]} ·{' '}
        {formatDistance(distance)} {t.away}
      </div>
      <Meta place={place} t={t} />
      <BuzzLine place={place} lang={lang} t={t} />
      {place.ratingCount !== undefined && <div className="muted small">{place.ratingCount.toLocaleString()} {t.reviews}</div>}
      {place.address && <p>{place.address}</p>}

      <div className="actions">
        <a className="btn btn--primary" href={directionsUrl(place)} target="_blank" rel="noreferrer">
          🧭 {t.directions}
        </a>
        <a className="btn" href={mapsUrl(place)} target="_blank" rel="noreferrer">
          {t.openInGoogleMaps}
        </a>
      </div>

      {place.ranking && <WhyLevel ranking={place.ranking} lang={lang} t={t} />}

      {place.hours?.length ? (
        <section>
          <h3>{t.hours}</h3>
          <ul className="hours">
            {place.hours.map((h) => (
              <li key={h}>{h}</li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}
