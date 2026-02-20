import { ttlCache } from './cache';

const DEFAULT_RATE = 1300;

export const fetchUsdToKrwRate = async (ttlSeconds: number): Promise<number> => {
  const cacheKey = 'usdkrw';
  const cached = ttlCache.get<number>(cacheKey);
  if (cached) return cached;

  try {
    const res = await fetch('https://open.er-api.com/v6/latest/USD').then((r) => r.json());
    const rate = Number(res?.rates?.KRW || DEFAULT_RATE);
    ttlCache.set(cacheKey, rate, ttlSeconds);
    return rate;
  } catch {
    return DEFAULT_RATE;
  }
};

export const fetchPricesInUsdt = async (
  ids: string[],
  apiBase: string,
  ttlSeconds: number
): Promise<Record<string, number>> => {
  if (!ids.length) return {};
  const deduped = [...new Set(ids)].sort();
  const key = `prices:${deduped.join(',')}`;
  const cached = ttlCache.get<Record<string, number>>(key);
  if (cached) return cached;

  const url = `${apiBase}/simple/price?ids=${encodeURIComponent(deduped.join(','))}&vs_currencies=usd`;
  const data = await fetch(url).then((r) => r.json());

  const prices: Record<string, number> = {};
  for (const id of deduped) {
    prices[id] = Number(data[id]?.usd ?? 0);
  }

  ttlCache.set(key, prices, ttlSeconds);
  return prices;
};
