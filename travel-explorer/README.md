# Travel Explorer 📍

Find restaurants, cafés, bars, attractions, nature, photo spots, entertainment and shopping
around you — or anywhere you're travelling — on an interactive Google Map.

- **8 category chips** you can combine (🍜 🍸 ☕ 🏛️ 🌿 📸 🎡 🛍️)
- **Live map**: pins for every result; drag the map and tap **Search this area**
- **Jump to any city** with the search box, or tap ◎ to use your GPS location
- **Filters**: minimum rating, max price, open now, radius (500 m – 5 km), sort by distance / rating
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
around Kyoto (landmark names are real, ratings and the restaurants/bars are made up).

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
  Explorer.tsx          main screen: search, chips, filters, list/detail, map
  categories.ts         category → place type mapping
  i18n.ts               English / 繁體中文 strings
  data/googlePlaces.ts  Places API (New) search
  data/demoPlaces.ts    sample Kyoto data for demo mode
  components/           map views, list, detail, filters
```

## Scripts

| Command | What it does |
|---|---|
| `npm run dev` | Dev server with hot reload |
| `npm run build` | Type-check and build to `dist/` (static files, deploy anywhere) |
| `npm run preview` | Serve the built `dist/` locally |
