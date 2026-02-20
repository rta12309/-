export type ChainId = 'ethereum' | 'solana';

export interface ChainDefinition {
  id: ChainId;
  displayName: string;
  nativeSymbol: string;
  explorerBaseUrl: string;
  addressPathTemplate: string;
  tokenPathTemplate?: string;
}

export interface AssetBalance {
  chainId: ChainId;
  symbol: string;
  name: string;
  amount: number;
  contractAddress?: string;
  isNative: boolean;
  coingeckoId?: string;
}

export interface WalletAddress {
  id: string;
  groupId: string;
  chainId: ChainId;
  address: string;
  alias: string;
}

export interface Group {
  id: string;
  name: string;
}

export interface AddressPortfolio {
  wallet: WalletAddress;
  assets: AssetValuation[];
  totalUsdt: number;
  totalKrw: number;
  error?: string;
  explorerUrl: string;
}

export interface AssetValuation extends AssetBalance {
  priceUsdt: number;
  valueUsdt: number;
  valueKrw: number;
}

export interface GroupPortfolio {
  group: Group;
  addresses: AddressPortfolio[];
  aggregatedAssets: AssetValuation[];
  totalUsdt: number;
  totalKrw: number;
}

export interface AppSettings {
  hideZeroValue: boolean;
  ttlSeconds: number;
  coingeckoApiBase: string;
}

export interface ImportExportData {
  groups: Group[];
  wallets: WalletAddress[];
  settings: AppSettings;
}
