// Small localStorage cache with expiry; failures (private mode, full storage) just mean no caching.

export function cacheGet<T>(key: string): T | undefined {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return undefined;
    const { exp, value } = JSON.parse(raw) as { exp: number; value: T };
    if (Date.now() > exp) {
      localStorage.removeItem(key);
      return undefined;
    }
    return value;
  } catch {
    return undefined;
  }
}

export function cacheSet<T>(key: string, value: T, ttlMs: number): void {
  try {
    localStorage.setItem(key, JSON.stringify({ exp: Date.now() + ttlMs, value }));
  } catch {
    // ignore
  }
}
