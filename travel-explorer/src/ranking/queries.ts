import type { CategoryId, QueryLang } from '../types';

// Which language the locals search in, by ISO country code.
const COUNTRY_LANG: Record<string, QueryLang> = {
  JP: 'ja', KR: 'ko', HK: 'zh-HK', MO: 'zh-HK', TW: 'zh-TW', CN: 'zh-CN', TH: 'th',
  FR: 'fr', BE: 'fr', MC: 'fr', ES: 'es', MX: 'es', AR: 'es', CL: 'es', CO: 'es', PE: 'es',
  DE: 'de', AT: 'de', CH: 'de', IT: 'it',
};

/** Places where the country itself is "the city" for search purposes. */
export const CITY_STATES = new Set(['HK', 'MO', 'SG', 'MC']);

export function localLangFor(countryCode?: string): QueryLang | undefined {
  return countryCode ? COUNTRY_LANG[countryCode.toUpperCase()] : undefined;
}

/** English + Chinese (Traditional) + the destination's own language, without duplicates. */
export function rankingLangs(countryCode?: string): QueryLang[] {
  return [...new Set<QueryLang>(['en', 'zh-TW', localLangFor(countryCode) ?? 'en'])];
}

// "{city}" is replaced by the city's name in that language.
const TEMPLATES: Record<QueryLang, Record<CategoryId, string>> = {
  en: {
    restaurant: 'best restaurants in {city}', cafe: 'best cafes in {city}', bar: 'best bars in {city}',
    attractions: 'best things to do in {city}', nature: 'best nature spots in {city}', photo: 'best photo spots in {city}',
    entertainment: 'best nightlife and entertainment in {city}', shopping: 'best shopping in {city}',
  },
  'zh-TW': {
    restaurant: '{city} 餐廳 推薦', cafe: '{city} 咖啡廳 推薦', bar: '{city} 酒吧 推薦', attractions: '{city} 景點 推薦',
    nature: '{city} 自然景點 推薦', photo: '{city} 拍照景點 推薦', entertainment: '{city} 娛樂 推薦', shopping: '{city} 購物 推薦',
  },
  'zh-HK': {
    restaurant: '{city} 餐廳 推介', cafe: '{city} cafe 推介', bar: '{city} 酒吧 推介', attractions: '{city} 好去處 推介',
    nature: '{city} 行山 大自然 推介', photo: '{city} 打卡 影相 推介', entertainment: '{city} 娛樂 好去處', shopping: '{city} 購物 推介',
  },
  'zh-CN': {
    restaurant: '{city} 餐厅 推荐', cafe: '{city} 咖啡馆 推荐', bar: '{city} 酒吧 推荐', attractions: '{city} 景点 推荐',
    nature: '{city} 自然风光 推荐', photo: '{city} 拍照打卡 推荐', entertainment: '{city} 娱乐 推荐', shopping: '{city} 购物 推荐',
  },
  ja: {
    restaurant: '{city} レストラン おすすめ', cafe: '{city} カフェ おすすめ', bar: '{city} バー おすすめ',
    attractions: '{city} 観光スポット おすすめ', nature: '{city} 自然 絶景 おすすめ', photo: '{city} 撮影スポット おすすめ',
    entertainment: '{city} 遊び おすすめ', shopping: '{city} ショッピング おすすめ',
  },
  ko: {
    restaurant: '{city} 맛집 추천', cafe: '{city} 카페 추천', bar: '{city} 바 추천', attractions: '{city} 관광지 추천',
    nature: '{city} 자연 명소 추천', photo: '{city} 포토스팟 추천', entertainment: '{city} 놀거리 추천', shopping: '{city} 쇼핑 추천',
  },
  th: {
    restaurant: 'ร้านอาหาร {city} แนะนำ', cafe: 'คาเฟ่ {city} แนะนำ', bar: 'บาร์ {city} แนะนำ', attractions: 'ที่เที่ยว {city} แนะนำ',
    nature: 'ธรรมชาติ {city} แนะนำ', photo: 'จุดถ่ายรูป {city} แนะนำ', entertainment: 'สถานบันเทิง {city} แนะนำ', shopping: 'ช้อปปิ้ง {city} แนะนำ',
  },
  fr: {
    restaurant: 'meilleurs restaurants {city}', cafe: 'meilleurs cafés {city}', bar: 'meilleurs bars {city}',
    attractions: 'que voir à {city}', nature: 'nature autour de {city}', photo: 'plus beaux points de vue {city}',
    entertainment: 'sortir à {city}', shopping: 'shopping {city}',
  },
  es: {
    restaurant: 'mejores restaurantes en {city}', cafe: 'mejores cafeterías en {city}', bar: 'mejores bares en {city}',
    attractions: 'qué ver en {city}', nature: 'naturaleza cerca de {city}', photo: 'mejores miradores en {city}',
    entertainment: 'ocio en {city}', shopping: 'compras en {city}',
  },
  de: {
    restaurant: 'beste Restaurants {city}', cafe: 'beste Cafés {city}', bar: 'beste Bars {city}',
    attractions: 'Sehenswürdigkeiten {city}', nature: 'Natur Ausflugsziele {city}', photo: 'Fotospots {city}',
    entertainment: 'Unterhaltung {city}', shopping: 'Shopping {city}',
  },
  it: {
    restaurant: 'migliori ristoranti {city}', cafe: 'migliori caffè {city}', bar: 'migliori bar {city}',
    attractions: 'cosa vedere a {city}', nature: 'natura vicino a {city}', photo: 'punti panoramici {city}',
    entertainment: 'divertimento {city}', shopping: 'shopping {city}',
  },
};

export function buildQuery(lang: QueryLang, category: CategoryId, city: string): string {
  return TEMPLATES[lang][category].replace('{city}', city);
}

/** YouTube `relevanceLanguage` codes. */
export const YOUTUBE_LANG: Record<QueryLang, string> = {
  en: 'en', 'zh-TW': 'zh-Hant', 'zh-HK': 'zh-Hant', 'zh-CN': 'zh-Hans', ja: 'ja', ko: 'ko', th: 'th',
  fr: 'fr', es: 'es', de: 'de', it: 'it',
};

/** Brave Search `search_lang` codes (note Brave uses "jp" for Japanese). */
export const BRAVE_LANG: Record<QueryLang, string> = {
  en: 'en', 'zh-TW': 'zh-hant', 'zh-HK': 'zh-hant', 'zh-CN': 'zh-hans', ja: 'jp', ko: 'ko', th: 'th',
  fr: 'fr', es: 'es', de: 'de', it: 'it',
};

export function isQueryLang(s: unknown): s is QueryLang {
  return typeof s === 'string' && s in TEMPLATES;
}
