# Travel Explorer 📍

Find restaurants, cafés, bars, attractions, nature, photo spots, entertainment and shopping
around you — or anywhere you're travelling — on an interactive Google Map.

- **8 category chips** you can combine (🍜 🍸 ☕ 🏛️ 🌿 📸 🎡 🛍️)
- **Ranked before you see them**: every place gets a level **S 必去 / A 強烈推薦 / B 值得一去 / C 在地選擇**
  from Google reviews *plus* YouTube videos, travel blog articles and Wikivoyage guides — see
  [How places are ranked](#how-places-are-ranked)
- **Live map**: pins for every result; drag the map and tap **Search this area**
- **Jump to any city** with the search box, or tap ◎ to use your GPS location
- **Filters**: minimum rating, max price, open now, radius (500 m – 5 km), sort by recommended level / distance / rating
- **Place details**: photos, rating, price, opening hours, one-tap **Directions** in Google Maps
- **Saved places** (♥), kept in your browser
- **English / 繁體中文** toggle (place names are fetched in the selected language)
- Works on phones; can be added to the home screen

## Quick start

```bash
cd travel-explorer
npm install
npm run dev        # open the printed http://localhost:5173 URL
```

Without an API key the app runs in **demo mode**: an OpenStreetMap map with sample places
around Kyoto (landmark names are real; ratings, video/article counts and the restaurants/bars are
made up — the evidence links open real searches for each place).

## Using real Google data

1. In [Google Cloud Console](https://console.cloud.google.com/), create a project and enable billing.
2. Enable **Maps JavaScript API** and **Places API (New)**.
3. Create an API key (APIs & Services → Credentials) and **restrict it**:
   - Application restriction: *Websites*, add `http://localhost:5173/*` and your deployed domain.
   - API restriction: only the two APIs above.
4. Copy `.env.example` to `.env.local` and set `VITE_GOOGLE_MAPS_API_KEY=...`
   (`.env.local` is git-ignored — never commit your key).
5. Restart `npm run dev`.

Optional: create a Map ID (Google Maps Platform → Map Management) and set `VITE_GOOGLE_MAP_ID`;
otherwise Google's development `DEMO_MAP_ID` is used.

**Cost:** each category you have switched on is one Nearby Search request per search
(📸 Photo spots adds one Text Search), and photos are billed when displayed. Google's monthly
free usage normally covers personal trip use, but set a
[budget alert](https://cloud.google.com/billing/docs/how-to/budgets) to be safe.

## How places are ranked

After the map search, and before anything is shown, each place gets a 0–100 score:

| Part | Weight | Source | How |
|---|---|---|---|
| Review quality | 30% | Google | Star rating pulled toward 4.0★ when there are few reviews, so 4.9★ from 12 reviews doesn't beat 4.6★ from 8,000 |
| Review volume | 20% | Google | Number of reviews, log scale (10,000+ = full marks) |
| YouTube videos | 25% | YouTube Data API | "best cafes in Kyoto"-style searches; the place counts when a video's title or description names it. Total views (10M = full) 70% + number of videos (5+ = full) 30% |
| Articles & guides | 25% | Brave Search + Wikivoyage | Listed in the city's Wikivoyage guide (40%) + mentioned in the top "best X in <city>" blog articles (3+ = full, 60%) |

| Level | Label | Rule |
|---|---|---|
| **S** | 🏆 Must-go 必去 | score ≥ 80 **and** mentioned by ≥ 2 sources beyond Google (videos / Wikivoyage / articles) |
| **A** | 🔥 Highly recommended 強烈推薦 | score 65–79 (or 80+ without enough outside sources) |
| **B** | 👍 Worth a visit 值得一去 | score 45–64 |
| **C** | 📍 Local pick 在地選擇 | below 45 |

- **Languages:** videos and articles are searched in **English, Traditional Chinese, and the language of the
  country you're in**, e.g. Hong Kong → Cantonese phrasing (「香港 好去處 推介」), Japan → Japanese
  (「京都 カフェ おすすめ」). Place names are fetched in each of those languages so that
  "Kiyomizu-dera", 「清水寺」 and 「清水寺」 all count as the same place. Supported local languages: see
  `src/ranking/queries.ts`.
- **Evidence:** tap a place → **Why this level** shows the score breakdown and links to the actual videos,
  articles and Wikivoyage page.
- **If a source is unavailable** (no key, quota used up, server not deployed), it's left out and the other
  weights are scaled up — it doesn't drag scores to zero. A note under the tabs says what was skipped.
- **Not included:** Instagram, TikTok, Xiaohongshu (小紅書) have no public search API; scraping them breaks
  their terms.
- **Matching is by name**, so a video that calls a place by a nickname can be missed, and very generic names
  ("Park", "Cafe") are ignored on purpose.

### Setting up the ranking sources

| Source | What you need | Free allowance |
|---|---|---|
| YouTube | Enable **YouTube Data API v3** in the same Google Cloud project (and add it to the key's API restrictions), or set a separate `VITE_YOUTUBE_API_KEY` | 100 searches/day. One area search uses *categories × languages* searches (3 × 3 = 9), so ≈ 11 new areas a day; results are cached 24 h per city + category |
| Wikivoyage | Nothing | Free, no key; cached 7 days |
| Blog articles | A [Brave Search API](https://brave.com/search/api/) key in `BRAVE_API_KEY` (server-side, **no** `VITE_` prefix) | $5 credit/month ≈ 1,000 searches. Not cached (Brave's terms forbid storing results) |

The Brave key must stay secret, so article search runs on a tiny server endpoint, `/api/articles`
([`server/articles.ts`](server/articles.ts)):

- **Locally:** put `BRAVE_API_KEY=...` in `.env.local`; `npm run dev` / `npm run preview` serve the endpoint.
- **Deployed:** the included Cloudflare Worker serves both the app and the endpoint:
  ```bash
  npm run build                         # VITE_* keys from .env.local are baked into the app here
  npx wrangler secret put BRAVE_API_KEY
  npx wrangler deploy
  ```
  Set `ALLOWED_ORIGINS` (in `wrangler.jsonc` `vars`) to your site's URL so others can't spend your credits.
  The endpoint only fetches pages that Brave returns, never URLs sent by the browser.

**Extra Google cost from ranking:** to learn place names in the other two languages, each category's
Nearby Search runs twice more with a names-only field list, so Places requests roughly triple.

## How categories map to Google place types

Defined in [`src/categories.ts`](src/categories.ts) — edit it to add or change categories.

| Category | Google Places (New) types |
|---|---|
| 🍜 Restaurants | `restaurant` |
| ☕ Cafés | `cafe`, `coffee_shop`, `bakery` |
| 🍸 Bars | `bar`, `pub`, `wine_bar` |
| 🏛️ Attractions | `tourist_attraction`, `museum`, `historical_landmark`, `art_gallery` |
| 🌿 Nature | `park`, `national_park`, `hiking_area`, `beach`, `botanical_garden` |
| 📸 Photo spots | `observation_deck` + text search "scenic viewpoint" |
| 🎡 Entertainment | `amusement_park`, `night_club`, `movie_theater`, `karaoke`, `bowling_alley`, `aquarium`, `zoo` |
| 🛍️ Shopping | `shopping_mall`, `market` |

## Project layout

```
src/
  App.tsx               picks Google mode (API key set) or demo mode
  Explorer.tsx          main screen: search → multilingual names → ranking → list/map
  categories.ts         category → place type mapping
  i18n.ts               English / 繁體中文 strings
  data/googlePlaces.ts  Places API (New) search
  data/demoPlaces.ts    sample Kyoto data (incl. made-up buzz numbers) for demo mode
  ranking/              score.ts (weights, levels), live.ts (collects signals), youtube.ts,
                        wikivoyage.ts, articlesClient.ts, match.ts (name matching), queries.ts
  components/           map views, list, detail, "Why this level", filters
server/articles.ts      /api/articles: Brave Search + article reading (key stays server-side)
worker/index.ts         Cloudflare Worker serving dist/ + /api/articles
tests/                  unit tests (npm test)
```

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Dev server with hot reload |
| `npm run build` | Type-check and build to `dist/` |
| `npm test` | Unit tests (scoring, name matching, article server, signal collection) |
| `npm run preview` | Serve the built `dist/` locally |
