import { useMemo, useState } from 'react';
import { APIProvider, useMapsLibrary } from '@vis.gl/react-google-maps';
import { DemoMapView } from './components/DemoMapView';
import { GoogleMapView } from './components/GoogleMapView';
import { createDemoBackend, createDemoSignalProvider, DEMO_CENTER } from './data/demoPlaces';
import { createGoogleBackend } from './data/googlePlaces';
import { Explorer } from './Explorer';
import { detectLang } from './i18n';
import { createLiveSignalProvider } from './ranking/live';
import type { Lang } from './types';

const API_KEY: string | undefined = import.meta.env.VITE_GOOGLE_MAPS_API_KEY || undefined;
const LANG_KEY = 'travel-explorer:lang';

const liveSignals = createLiveSignalProvider({
  youtubeKey: import.meta.env.VITE_YOUTUBE_API_KEY || API_KEY,
  articlesEndpoint: import.meta.env.VITE_ARTICLES_ENDPOINT || '/api/articles',
});

function loadLang(): Lang {
  try {
    const saved = localStorage.getItem(LANG_KEY);
    if (saved === 'en' || saved === 'zh-TW') return saved;
  } catch {
    // ignore
  }
  return detectLang();
}

type ExplorerShellProps = { lang: Lang; onLangChange(l: Lang): void };

function GoogleExplorer(props: ExplorerShellProps) {
  const places = useMapsLibrary('places');
  const backend = useMemo(() => createGoogleBackend(places), [places]);
  return <Explorer backend={backend} signals={liveSignals} MapView={GoogleMapView} initialCenter={DEMO_CENTER} {...props} />;
}

const demoBackend = createDemoBackend();
const demoSignals = createDemoSignalProvider();

export default function App() {
  const [lang, setLang] = useState<Lang>(loadLang);
  // The Maps script language is fixed once loaded; search results still follow `lang` per request.
  const [mapsLang] = useState(lang);

  const onLangChange = (l: Lang) => {
    setLang(l);
    try {
      localStorage.setItem(LANG_KEY, l);
    } catch {
      // ignore
    }
  };

  if (!API_KEY) {
    return (
      <Explorer
        backend={demoBackend}
        signals={demoSignals}
        MapView={DemoMapView}
        initialCenter={DEMO_CENTER}
        lang={lang}
        onLangChange={onLangChange}
      />
    );
  }
  return (
    <APIProvider apiKey={API_KEY} language={mapsLang} libraries={['places', 'marker']}>
      <GoogleExplorer lang={lang} onLangChange={onLangChange} />
    </APIProvider>
  );
}
