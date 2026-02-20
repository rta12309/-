import { create } from 'zustand';
import type { AppSettings, Group, ImportExportData, WalletAddress } from './types/models';
import { makeId } from './utils/format';

interface AppState {
  groups: Group[];
  wallets: WalletAddress[];
  settings: AppSettings;
  etherscanApiKey: string;
  addGroup: (name: string) => void;
  renameGroup: (id: string, name: string) => void;
  deleteGroup: (id: string) => void;
  addWallet: (wallet: Omit<WalletAddress, 'id'>) => void;
  removeWallet: (id: string) => void;
  setSettings: (partial: Partial<AppSettings>) => void;
  setEtherscanApiKey: (value: string) => void;
  importData: (payload: ImportExportData) => void;
}

const defaultSettings: AppSettings = {
  hideZeroValue: false,
  ttlSeconds: 120,
  coingeckoApiBase: 'https://api.coingecko.com/api/v3'
};

const storageKey = 'multi-chain-dashboard-state';

const loadState = () => {
  try {
    const raw = localStorage.getItem(storageKey);
    if (!raw) return undefined;
    return JSON.parse(raw) as Pick<AppState, 'groups' | 'wallets' | 'settings' | 'etherscanApiKey'>;
  } catch {
    return undefined;
  }
};

const persist = (state: Pick<AppState, 'groups' | 'wallets' | 'settings' | 'etherscanApiKey'>) => {
  localStorage.setItem(storageKey, JSON.stringify(state));
};

const initial = loadState();

export const useAppStore = create<AppState>((set, get) => ({
  groups: initial?.groups ?? [{ id: makeId(), name: '기본 그룹' }],
  wallets: initial?.wallets ?? [],
  settings: initial?.settings ?? defaultSettings,
  etherscanApiKey: initial?.etherscanApiKey ?? import.meta.env.VITE_ETHERSCAN_API_KEY ?? '',
  addGroup: (name) => {
    const groups = [...get().groups, { id: makeId(), name }];
    set({ groups });
    persist({ groups, wallets: get().wallets, settings: get().settings, etherscanApiKey: get().etherscanApiKey });
  },
  renameGroup: (id, name) => {
    const groups = get().groups.map((group) => (group.id === id ? { ...group, name } : group));
    set({ groups });
    persist({ groups, wallets: get().wallets, settings: get().settings, etherscanApiKey: get().etherscanApiKey });
  },
  deleteGroup: (id) => {
    const groups = get().groups.filter((group) => group.id !== id);
    const wallets = get().wallets.filter((wallet) => wallet.groupId !== id);
    const nextGroups = groups.length ? groups : [{ id: makeId(), name: '기본 그룹' }];
    set({ groups: nextGroups, wallets });
    persist({ groups: nextGroups, wallets, settings: get().settings, etherscanApiKey: get().etherscanApiKey });
  },
  addWallet: (wallet) => {
    const wallets = [...get().wallets, { ...wallet, id: makeId() }];
    set({ wallets });
    persist({ groups: get().groups, wallets, settings: get().settings, etherscanApiKey: get().etherscanApiKey });
  },
  removeWallet: (id) => {
    const wallets = get().wallets.filter((wallet) => wallet.id !== id);
    set({ wallets });
    persist({ groups: get().groups, wallets, settings: get().settings, etherscanApiKey: get().etherscanApiKey });
  },
  setSettings: (partial) => {
    const settings = { ...get().settings, ...partial };
    set({ settings });
    persist({ groups: get().groups, wallets: get().wallets, settings, etherscanApiKey: get().etherscanApiKey });
  },
  setEtherscanApiKey: (value) => {
    set({ etherscanApiKey: value });
    persist({ groups: get().groups, wallets: get().wallets, settings: get().settings, etherscanApiKey: value });
  },
  importData: (payload) => {
    set({ groups: payload.groups, wallets: payload.wallets, settings: payload.settings });
    persist({ groups: payload.groups, wallets: payload.wallets, settings: payload.settings, etherscanApiKey: get().etherscanApiKey });
  }
}));
