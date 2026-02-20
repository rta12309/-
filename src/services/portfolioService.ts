import { chainAdapters } from '../adapters/chainAdapters';
import type { AddressPortfolio, AppSettings, AssetValuation, Group, GroupPortfolio, WalletAddress } from '../types/models';
import { fetchPricesInUsdt, fetchUsdToKrwRate } from './pricingService';
import { ttlCache } from './cache';

const fallbackCoingecko: Record<string, string> = {
  ETH: 'ethereum',
  SOL: 'solana',
  USDT: 'tether',
  USDC: 'usd-coin'
};

const getAssetKey = (asset: AssetValuation): string => `${asset.chainId}:${asset.symbol}:${asset.contractAddress ?? 'native'}`;

export const fetchAddressPortfolio = async (
  wallet: WalletAddress,
  settings: AppSettings,
  etherscanApiKey?: string
): Promise<AddressPortfolio> => {
  const cacheKey = `portfolio:${wallet.chainId}:${wallet.address}`;
  const cached = ttlCache.get<AddressPortfolio>(cacheKey);
  if (cached) return cached;

  try {
    const adapter = chainAdapters[wallet.chainId];
    const balances = await adapter.fetchBalances(wallet.address, etherscanApiKey);
    const coinIds = balances.map((b) => b.coingeckoId ?? fallbackCoingecko[b.symbol] ?? '').filter(Boolean);
    const [prices, usdKrw] = await Promise.all([
      fetchPricesInUsdt(coinIds, settings.coingeckoApiBase, settings.ttlSeconds),
      fetchUsdToKrwRate(settings.ttlSeconds)
    ]);

    const assets: AssetValuation[] = balances.map((b) => {
      const id = b.coingeckoId ?? fallbackCoingecko[b.symbol] ?? '';
      const priceUsdt = id ? prices[id] ?? 0 : 0;
      const valueUsdt = b.amount * priceUsdt;
      return {
        ...b,
        priceUsdt,
        valueUsdt,
        valueKrw: valueUsdt * usdKrw
      };
    });

    const result: AddressPortfolio = {
      wallet,
      assets,
      totalUsdt: assets.reduce((sum, asset) => sum + asset.valueUsdt, 0),
      totalKrw: assets.reduce((sum, asset) => sum + asset.valueKrw, 0),
      explorerUrl: adapter.buildExplorerUrl(wallet.address)
    };

    ttlCache.set(cacheKey, result, settings.ttlSeconds);
    return result;
  } catch (error) {
    return {
      wallet,
      assets: [],
      totalUsdt: 0,
      totalKrw: 0,
      explorerUrl: chainAdapters[wallet.chainId].buildExplorerUrl(wallet.address),
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
};

export const aggregateGroupPortfolio = (group: Group, addressPortfolios: AddressPortfolio[]): GroupPortfolio => {
  const map = new Map<string, AssetValuation>();

  for (const portfolio of addressPortfolios) {
    for (const asset of portfolio.assets) {
      const key = getAssetKey(asset);
      const existing = map.get(key);
      if (!existing) {
        map.set(key, { ...asset });
      } else {
        existing.amount += asset.amount;
        existing.valueUsdt += asset.valueUsdt;
        existing.valueKrw += asset.valueKrw;
      }
    }
  }

  return {
    group,
    addresses: addressPortfolios,
    aggregatedAssets: Array.from(map.values()).sort((a, b) => b.valueUsdt - a.valueUsdt),
    totalUsdt: addressPortfolios.reduce((sum, p) => sum + p.totalUsdt, 0),
    totalKrw: addressPortfolios.reduce((sum, p) => sum + p.totalKrw, 0)
  };
};
