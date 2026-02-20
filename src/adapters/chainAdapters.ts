import type { AssetBalance, ChainDefinition, ChainId } from '../types/models';

export interface ChainAdapter {
  definition: ChainDefinition;
  validateAddress: (address: string) => boolean;
  fetchBalances: (address: string, apiKey?: string) => Promise<AssetBalance[]>;
  buildExplorerUrl: (address: string) => string;
}

const chainDefinitions: Record<ChainId, ChainDefinition> = {
  ethereum: {
    id: 'ethereum',
    displayName: 'Ethereum',
    nativeSymbol: 'ETH',
    explorerBaseUrl: 'https://etherscan.io',
    addressPathTemplate: '/address/{address}',
    tokenPathTemplate: '/token/{tokenAddress}'
  },
  solana: {
    id: 'solana',
    displayName: 'Solana',
    nativeSymbol: 'SOL',
    explorerBaseUrl: 'https://solscan.io',
    addressPathTemplate: '/account/{address}',
    tokenPathTemplate: '/token/{tokenAddress}'
  }
};

const buildExplorerUrl = (chainId: ChainId, address: string) => {
  const def = chainDefinitions[chainId];
  return `${def.explorerBaseUrl}${def.addressPathTemplate.replace('{address}', address)}`;
};

const ETHERSCAN_API_BASE = 'https://api.etherscan.io/api';
const SOLANA_PUBLIC_RPC = 'https://api.mainnet-beta.solana.com';

const knownErc20Coingecko: Record<string, string> = {
  usdt: 'tether',
  usdc: 'usd-coin',
  dai: 'dai',
  weth: 'weth',
  wbtc: 'wrapped-bitcoin'
};

const knownSplCoingecko: Record<string, string> = {
  SOL: 'solana',
  USDC: 'usd-coin',
  USDT: 'tether',
  BONK: 'bonk'
};

const fetchEthereumBalances = async (address: string, apiKey?: string): Promise<AssetBalance[]> => {
  const keyParam = apiKey ? `&apikey=${apiKey}` : '';

  const nativeResponse = await fetch(
    `${ETHERSCAN_API_BASE}?module=account&action=balance&address=${address}&tag=latest${keyParam}`
  ).then((r) => r.json());

  if (nativeResponse.status !== '1') {
    throw new Error(nativeResponse.result || 'Ethereum native balance fetch failed');
  }

  const tokenResponse = await fetch(
    `${ETHERSCAN_API_BASE}?module=account&action=tokentx&address=${address}&page=1&offset=200&sort=desc${keyParam}`
  ).then((r) => r.json());

  const balances = new Map<string, AssetBalance>();
  const nativeAmount = Number(nativeResponse.result) / 10 ** 18;

  balances.set('native', {
    chainId: 'ethereum',
    symbol: 'ETH',
    name: 'Ethereum',
    amount: nativeAmount,
    isNative: true,
    coingeckoId: 'ethereum'
  });

  if (tokenResponse.status === '1' && Array.isArray(tokenResponse.result)) {
    for (const tx of tokenResponse.result) {
      const symbol = String(tx.tokenSymbol || '').toUpperCase();
      if (!symbol || !tx.contractAddress) continue;
      const decimals = Number(tx.tokenDecimal || 0);
      const value = Number(tx.value || 0) / 10 ** decimals;
      const key = tx.contractAddress.toLowerCase();
      const current = balances.get(key);
      const delta = tx.to?.toLowerCase() === address.toLowerCase() ? value : -value;
      const nextAmount = (current?.amount ?? 0) + delta;
      balances.set(key, {
        chainId: 'ethereum',
        symbol,
        name: tx.tokenName || symbol,
        amount: Math.max(nextAmount, 0),
        contractAddress: tx.contractAddress,
        isNative: false,
        coingeckoId: knownErc20Coingecko[symbol.toLowerCase()]
      });
    }
  }

  return Array.from(balances.values());
};

const fetchSolanaBalances = async (address: string): Promise<AssetBalance[]> => {
  const payload = (method: string, params: unknown[]) => ({
    jsonrpc: '2.0',
    id: 1,
    method,
    params
  });

  const native = await fetch(SOLANA_PUBLIC_RPC, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload('getBalance', [address]))
  }).then((r) => r.json());

  if (native.error) {
    throw new Error(native.error.message || 'Solana native balance fetch failed');
  }

  const tokenAccounts = await fetch(SOLANA_PUBLIC_RPC, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(
      payload('getParsedTokenAccountsByOwner', [address, { programId: 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA' }, { encoding: 'jsonParsed' }])
    )
  }).then((r) => r.json());

  const assets: AssetBalance[] = [
    {
      chainId: 'solana',
      symbol: 'SOL',
      name: 'Solana',
      amount: Number(native.result.value) / 10 ** 9,
      isNative: true,
      coingeckoId: knownSplCoingecko.SOL
    }
  ];

  if (tokenAccounts.result?.value) {
    for (const account of tokenAccounts.result.value) {
      const info = account.account?.data?.parsed?.info;
      if (!info) continue;
      const tokenAmount = Number(info.tokenAmount?.uiAmount || 0);
      const mint = String(info.mint);
      const symbol = mint.slice(0, 4).toUpperCase();
      assets.push({
        chainId: 'solana',
        symbol,
        name: symbol,
        amount: tokenAmount,
        contractAddress: mint,
        isNative: false,
        coingeckoId: knownSplCoingecko[symbol]
      });
    }
  }

  return assets;
};

const ethereumAdapter: ChainAdapter = {
  definition: chainDefinitions.ethereum,
  validateAddress: (address) => /^0x[a-fA-F0-9]{40}$/.test(address),
  fetchBalances: fetchEthereumBalances,
  buildExplorerUrl: (address) => buildExplorerUrl('ethereum', address)
};

const solanaAdapter: ChainAdapter = {
  definition: chainDefinitions.solana,
  validateAddress: (address) => /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(address),
  fetchBalances: fetchSolanaBalances,
  buildExplorerUrl: (address) => buildExplorerUrl('solana', address)
};

export const chainAdapters: Record<ChainId, ChainAdapter> = {
  ethereum: ethereumAdapter,
  solana: solanaAdapter
};

export const supportedChains = Object.values(chainDefinitions);
