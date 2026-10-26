import type { Strings } from '../i18n';
import { WEIGHTS } from '../ranking/score';
import type { Lang, Ranking } from '../types';
import { compact, LevelBadge } from './PlaceBits';

function Bar({ label, weight, value, t }: { label: string; weight: number; value?: number; t: Strings }) {
  return (
    <div className="bar-row">
      <span className="bar-label">
        {label} <span className="muted">{Math.round(weight * 100)}%</span>
      </span>
      {value === undefined ? (
        <span className="muted small">{t.unavailable}</span>
      ) : (
        <span className="bar" aria-label={`${Math.round(value * 100)} / 100`}>
          <span style={{ width: `${Math.round(value * 100)}%` }} />
        </span>
      )}
    </div>
  );
}

export function WhyLevel({ ranking, lang, t }: { ranking: Ranking; lang: Lang; t: Strings }) {
  const { signals, parts } = ranking;
  const hasBuzz = signals.videos.length > 0 || signals.articles.length > 0 || signals.wikivoyage;
  return (
    <section className="why">
      <h3>{t.whyLevel}</h3>
      <div className="why-head">
        <LevelBadge level={ranking.level} t={t} withLabel />
        <span className="muted">
          {t.score} {ranking.score}/100
        </span>
      </div>
      {ranking.sample && <p className="muted small">{t.sampleData}</p>}
      {ranking.level === 'A' && ranking.score >= 80 && <p className="muted small">{t.sNeedsSources}</p>}

      <Bar label={t.partQuality} weight={WEIGHTS.quality} value={parts.quality} t={t} />
      <Bar label={t.partVolume} weight={WEIGHTS.volume} value={parts.volume} t={t} />
      <Bar label={t.partVideo} weight={WEIGHTS.video} value={parts.video} t={t} />
      <Bar label={t.partArticles} weight={WEIGHTS.articles} value={parts.articles} t={t} />

      {!hasBuzz && <p className="muted small">{t.noBuzz}</p>}

      {signals.videos.length > 0 && (
        <>
          <h4>▶ {t.videosHeading}</h4>
          <ul className="evidence">
            {signals.videos.slice(0, 3).map((v) => (
              <li key={v.id}>
                <a href={v.url} target="_blank" rel="noreferrer">
                  {v.title}
                </a>
                <span className="muted small">
                  {' '}
                  · {v.channel} · {compact(v.views, lang)} {t.views}
                </span>
              </li>
            ))}
            {signals.videos.length > 3 && <li className="muted small">{t.moreN(signals.videos.length - 3)}</li>}
          </ul>
        </>
      )}

      {(signals.articles.length > 0 || signals.wikivoyage) && (
        <>
          <h4>📰 {t.articlesHeading}</h4>
          <ul className="evidence">
            {signals.wikivoyage && (
              <li>
                🧭{' '}
                <a href={signals.wikivoyage.url} target="_blank" rel="noreferrer">
                  {t.wikivoyageListed}: {signals.wikivoyage.title}
                </a>
              </li>
            )}
            {signals.articles.slice(0, 5).map((a) => (
              <li key={a.url + a.title}>
                <a href={a.url} target="_blank" rel="noreferrer">
                  {a.title}
                </a>{' '}
                <span className="muted small">· {hostOf(a.url)}</span>
              </li>
            ))}
            {signals.articles.length > 5 && <li className="muted small">{t.moreN(signals.articles.length - 5)}</li>}
          </ul>
        </>
      )}
    </section>
  );
}

function hostOf(url: string) {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return '';
  }
}
