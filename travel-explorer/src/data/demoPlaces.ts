import type { Backend, CategoryId, LatLng, Place } from '../types';
import { distanceMeters } from '../geo';

// Sample data around central Kyoto, used when no API key is configured.
// Landmark names and coordinates are real; ratings, prices and hours are made up.
// Food/drink/entertainment venues are fictional so no real business gets invented reviews.
export const DEMO_CENTER: LatLng = { lat: 35.0036, lng: 135.7718 };

type DemoSeed = [name: string, nameZh: string, category: CategoryId, lat: number, lng: number,
  rating: number, ratingCount: number, price: number | undefined, open: [number, number]];

const SEEDS: DemoSeed[] = [
  ['Yasaka Shrine', '八坂神社', 'attractions', 35.0037, 135.7785, 4.5, 4210, undefined, [0, 24]],
  ['Kiyomizu-dera', '清水寺', 'attractions', 34.9949, 135.785, 4.6, 6120, 1, [6, 18]],
  ['Kyoto International Manga Museum', '京都國際漫畫博物館', 'attractions', 35.0117, 135.7594, 4.2, 980, 2, [10, 17]],
  ['Kennin-ji Temple', '建仁寺', 'attractions', 34.9985, 135.7737, 4.5, 1730, 1, [10, 17]],
  ['Maruyama Park', '圓山公園', 'nature', 35.0036, 135.7811, 4.4, 2300, undefined, [0, 24]],
  ['Kamo River Banks', '鴨川河岸', 'nature', 35.005, 135.7714, 4.6, 3100, undefined, [0, 24]],
  ['Shosei-en Garden', '涉成園', 'nature', 34.9917, 135.7622, 4.3, 640, 1, [9, 17]],
  ['Yasaka Pagoda (Hokan-ji)', '八坂塔（法觀寺）', 'photo', 34.9985, 135.7792, 4.6, 2900, undefined, [0, 24]],
  ['Hanamikoji Street', '花見小路', 'photo', 35.0026, 135.7752, 4.4, 2100, undefined, [0, 24]],
  ['Shirakawa Lane & Tatsumi Bridge', '白川巽橋', 'photo', 35.0059, 135.7745, 4.7, 1500, undefined, [0, 24]],
  ['Kyoto Tower Observation Deck', '京都塔展望台', 'photo', 34.9875, 135.7593, 4.1, 3800, 2, [10, 21]],
  ['Nishiki Market', '錦市場', 'shopping', 35.005, 135.7649, 4.3, 5200, 2, [9, 18]],
  ['Teramachi Shopping Arcade', '寺町通商店街', 'shopping', 35.0063, 135.768, 4.1, 1200, 2, [10, 20]],
  ['Riverside Udon House (sample)', '河畔烏龍麵屋（範例）', 'restaurant', 35.0042, 135.7706, 4.4, 820, 1, [11, 21]],
  ['Gion Kaiseki Table (sample)', '祇園懷石料理（範例）', 'restaurant', 35.0031, 135.7748, 4.7, 410, 4, [17, 22]],
  ['Pontocho Yakitori (sample)', '先斗町串燒（範例）', 'restaurant', 35.0061, 135.7712, 4.3, 560, 2, [17, 24]],
  ['Station Ramen Stand (sample)', '車站拉麵（範例）', 'restaurant', 34.9868, 135.7601, 4.0, 1300, 1, [11, 23]],
  ['Kamogawa Roasters (sample)', '鴨川烘豆咖啡（範例）', 'cafe', 35.0071, 135.7703, 4.6, 690, 1, [8, 18]],
  ['Matcha Corner (sample)', '抹茶小舖（範例）', 'cafe', 35.0019, 135.7765, 4.5, 920, 1, [10, 18]],
  ['Morning Bakery Sanjo (sample)', '三條晨光麵包（範例）', 'cafe', 35.0089, 135.7671, 4.3, 340, 1, [7, 17]],
  ['Lantern Sake Bar (sample)', '燈籠清酒吧（範例）', 'bar', 35.0058, 135.7709, 4.5, 270, 2, [18, 2]],
  ['Riverview Cocktail Lounge (sample)', '河景雞尾酒吧（範例）', 'bar', 35.0046, 135.771, 4.4, 380, 3, [19, 1]],
  ['Kiyamachi Craft Beer (sample)', '木屋町精釀啤酒（範例）', 'bar', 35.0069, 135.7708, 4.2, 210, 2, [16, 24]],
  ['Shijo Cinema (sample)', '四條電影院（範例）', 'entertainment', 35.0035, 135.7672, 4.1, 760, 2, [9, 24]],
  ['Gion Karaoke (sample)', '祇園卡拉OK（範例）', 'entertainment', 35.0041, 135.7741, 4.0, 330, 2, [12, 5]],
  ['Kyoto Aquarium', '京都水族館', 'entertainment', 34.9877, 135.7476, 4.2, 4500, 3, [10, 18]],
];

function kyotoHour(): number {
  return Number(new Intl.DateTimeFormat('en-US', { hour: 'numeric', hourCycle: 'h23', timeZone: 'Asia/Tokyo' }).format(new Date()));
}

function isOpen([from, to]: [number, number], hour: number): boolean {
  if (from === 0 && to === 24) return true;
  return from < to ? hour >= from && hour < to : hour >= from || hour < to; // overnight hours wrap
}

function hoursText([from, to]: [number, number]): string[] {
  const pad = (h: number) => `${String(h % 24).padStart(2, '0')}:00`;
  return [from === 0 && to === 24 ? 'Open 24 hours' : `Daily ${pad(from)} – ${pad(to)}`];
}

export function createDemoBackend(): Backend {
  return {
    kind: 'demo',
    ready: true,
    async search(center, radius, category, lang) {
      const hour = kyotoHour();
      return SEEDS.filter((s) => s[2] === category)
        .map(([name, nameZh, cat, lat, lng, rating, ratingCount, price, open], i): Place => ({
          id: `demo-${cat}-${i}`,
          name: lang === 'zh-TW' ? nameZh : name,
          category: cat,
          location: { lat, lng },
          address: 'Kyoto, Japan',
          rating,
          ratingCount,
          priceLevel: price,
          openNow: isOpen(open, hour),
          hours: hoursText(open),
        }))
        .filter((p) => distanceMeters(center, p.location) <= radius);
    },
  };
}
