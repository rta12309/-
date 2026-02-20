const MAX_WALLETS_PER_GROUP = 10;
const MIN_AUTO_REFRESH_SECONDS = 5;
const ETHERSCAN_V2_ENDPOINT = 'https://api.etherscan.io/v2/api';
const EXPLORER_V1_ENDPOINTS = {
  '1': 'https://api.etherscan.io/api',
  '56': 'https://api.bscscan.com/api',
  '137': 'https://api.polygonscan.com/api',
  '42161': 'https://api.arbiscan.io/api',
  '10': 'https://api-optimistic.etherscan.io/api',
  '43114': 'https://api.snowtrace.io/api',
  '8453': 'https://api.basescan.org/api',
};

const enabled = {
  upbit: true,
};

const SOURCES = [
  {
    key: 'ethereum',
    label: 'Ethereum (Ethplorer API + Etherscan)',
    chain: 'ethereum',
    explorerBase: 'https://etherscan.io/address/',
    apiExample: 'https://api.ethplorer.io/getAddressInfo/{address}?apiKey=freekey',
    fetcher: fetchEthereumWallet,
  },
  {
    key: 'solana',
    label: 'Solana (Solscan API)',
    chain: 'solana',
    explorerBase: 'https://solscan.io/account/',
    apiExample:
      'https://api-v2.solscan.io/v2/account/token-accounts?address={address}&page=1&page_size=40&type=token',
    fetcher: fetchSolanaWallet,
  },
  {
    key: 'bsc',
    label: 'BNB Smart Chain (RPC + CoinGecko)',
    chain: 'bsc',
    explorerBase: 'https://bscscan.com/address/',
    apiExample: 'https://bsc-dataseed.binance.org (eth_getBalance)',
    fetcher: (address) => fetchEvmWallet(address, '56', 'https://bsc-dataseed.binance.org', 'binancecoin', 'BNB'),
  },
  {
    key: 'polygon',
    label: 'Polygon (RPC + CoinGecko)',
    chain: 'polygon',
    explorerBase: 'https://polygonscan.com/address/',
    apiExample: 'https://polygon-rpc.com (eth_getBalance)',
    fetcher: (address) => fetchEvmWallet(address, '137', 'https://polygon-rpc.com', 'matic-network', 'MATIC'),
  },
  {
    key: 'arbitrum',
    label: 'Arbitrum (RPC + CoinGecko)',
    chain: 'arbitrum',
    explorerBase: 'https://arbiscan.io/address/',
    apiExample: 'https://arb1.arbitrum.io/rpc (eth_getBalance)',
    fetcher: (address) => fetchEvmWallet(address, '42161', 'https://arb1.arbitrum.io/rpc', 'ethereum', 'ETH'),
  },
  {
    key: 'optimism',
    label: 'Optimism (RPC + CoinGecko)',
    chain: 'optimism',
    explorerBase: 'https://optimistic.etherscan.io/address/',
    apiExample: 'https://mainnet.optimism.io (eth_getBalance)',
    fetcher: (address) => fetchEvmWallet(address, '10', 'https://mainnet.optimism.io', 'ethereum', 'ETH'),
  },
  {
    key: 'avalanche',
    label: 'Avalanche (RPC + CoinGecko)',
    chain: 'avalanche',
    explorerBase: 'https://snowtrace.io/address/',
    apiExample: 'https://api.avax.network/ext/bc/C/rpc (eth_getBalance)',
    fetcher: (address) =>
      fetchEvmWallet(address, '43114', 'https://api.avax.network/ext/bc/C/rpc', 'avalanche-2', 'AVAX'),
  },
  {
    key: 'base',
    label: 'Base (RPC + CoinGecko)',
    chain: 'base',
    explorerBase: 'https://basescan.org/address/',
    apiExample: 'https://mainnet.base.org (eth_getBalance)',
    fetcher: (address) => fetchEvmWallet(address, '8453', 'https://mainnet.base.org', 'ethereum', 'ETH'),
  },
  {
    key: 'tron',
    label: 'TRON (TronGrid API)',
    chain: 'tron',
    explorerBase: 'https://tronscan.org/#/address/',
    apiExample: 'https://api.trongrid.io/v1/accounts/{address}',
    fetcher: fetchTronWallet,
  },
  {
    key: 'bitcoin',
    label: 'Bitcoin (Blockstream API)',
    chain: 'bitcoin',
    explorerBase: 'https://blockstream.info/address/',
    apiExample: 'https://blockstream.info/api/address/{address}',
    fetcher: fetchBitcoinWallet,
  },
];

let usdtKrwRate = 0;
let elements = null;
let initialized = false;
let autoAnalyzeTimer = null;

function init() {
  if (initialized) return;

  elements = {
    groupList: document.getElementById('group-list'),
    addGroupBtn: document.getElementById('add-group-btn'),
    analyzeAllBtn: document.getElementById('analyze-all-btn'),
    refreshRateBtn: document.getElementById('refresh-rate-btn'),
    fxRateDisplay: document.getElementById('fx-rate-display'),
    groupTemplate: document.getElementById('group-template'),
    walletTemplate: document.getElementById('wallet-template'),
    autoRefreshToggle: document.getElementById('auto-refresh-toggle'),
    autoRefreshSeconds: document.getElementById('auto-refresh-seconds'),
  };

  if (!Object.values(elements).every(Boolean)) {
    console.error('필수 UI 요소를 찾을 수 없습니다.');
    return;
  }

  initialized = true;

  elements.refreshRateBtn.addEventListener('click', loadUpbitRate);
  elements.addGroupBtn.addEventListener('click', () => createGroup());
  elements.analyzeAllBtn.addEventListener('click', () => analyzeAllGroups(true));
  elements.autoRefreshToggle.addEventListener('change', updateAutoAnalyze);
  elements.autoRefreshSeconds.addEventListener('change', updateAutoAnalyze);

  createGroup('기본 그룹');
  loadUpbitRate();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

function updateAutoAnalyze() {
  if (autoAnalyzeTimer) {
    clearInterval(autoAnalyzeTimer);
    autoAnalyzeTimer = null;
  }

  if (!elements.autoRefreshToggle.checked) {
    return;
  }

  const seconds = Math.max(MIN_AUTO_REFRESH_SECONDS, Number(elements.autoRefreshSeconds.value || 0));
  elements.autoRefreshSeconds.value = String(seconds);

  analyzeAllGroups(false);
  autoAnalyzeTimer = setInterval(() => analyzeAllGroups(false), seconds * 1000);
}

function createGroup(defaultName = '') {
  const node = elements.groupTemplate.content.firstElementChild.cloneNode(true);
  const nameInput = node.querySelector('.group-name');
  const walletList = node.querySelector('.wallet-list');
  const addWalletBtn = node.querySelector('.add-wallet-btn');
  const removeGroupBtn = node.querySelector('.remove-group-btn');

  nameInput.value = defaultName;

  addWalletBtn.addEventListener('click', () => {
    if (walletList.children.length >= MAX_WALLETS_PER_GROUP) {
      alert(`지갑 입력칸은 최대 ${MAX_WALLETS_PER_GROUP}개까지 가능합니다.`);
      return;
    }
    walletList.appendChild(createWalletRow());
  });

  removeGroupBtn.addEventListener('click', () => {
    node.remove();
  });

  walletList.appendChild(createWalletRow());
  elements.groupList.appendChild(node);
}

function createWalletRow() {
  const row = elements.walletTemplate.content.firstElementChild.cloneNode(true);
  const sourceSelect = row.querySelector('.source-select');
  const walletInput = row.querySelector('.wallet-input');
  const explorerLink = row.querySelector('.explorer-link');
  const removeBtn = row.querySelector('.remove-wallet-btn');

  SOURCES.forEach((source) => {
    const option = document.createElement('option');
    option.value = source.key;
    option.textContent = source.label;
    sourceSelect.appendChild(option);
  });

  const updateLinks = () => {
    const source = getSourceConfig(sourceSelect.value);
    const address = walletInput.value.trim();
    const valid = isValidAddress(source.chain, address);

    setLinkDisabled(explorerLink, false);
    explorerLink.href = address && valid
      ? `${source.explorerBase}${encodeURIComponent(address)}`
      : source.explorerBase;
  };

  sourceSelect.addEventListener('change', updateLinks);
  walletInput.addEventListener('input', updateLinks);
  removeBtn.addEventListener('click', () => row.remove());

  updateLinks();
  return row;
}

function setLinkDisabled(linkEl, disabled, title = '') {
  if (disabled) {
    linkEl.href = '#';
    linkEl.classList.add('link-disabled');
    linkEl.setAttribute('aria-disabled', 'true');
    linkEl.title = title;
  } else {
    linkEl.classList.remove('link-disabled');
    linkEl.removeAttribute('aria-disabled');
    linkEl.removeAttribute('title');
  }
}

function getSourceConfig(key) {
  return SOURCES.find((source) => source.key === key) || SOURCES[0];
}

function isValidAddress(chain, address) {
  if (!address) return false;

  const checks = {
    ethereum: /^0x[a-fA-F0-9]{40}$/,
    bsc: /^0x[a-fA-F0-9]{40}$/,
    polygon: /^0x[a-fA-F0-9]{40}$/,
    arbitrum: /^0x[a-fA-F0-9]{40}$/,
    optimism: /^0x[a-fA-F0-9]{40}$/,
    avalanche: /^0x[a-fA-F0-9]{40}$/,
    base: /^0x[a-fA-F0-9]{40}$/,
    solana: /^[1-9A-HJ-NP-Za-km-z]{32,44}$/,
    tron: /^T[1-9A-HJ-NP-Za-km-z]{33}$/,
    bitcoin: /^(bc1[ac-hj-np-z02-9]{11,71}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})$/,
  };

  const rule = checks[chain];
  return rule ? rule.test(address) : address.length > 0;
}

async function loadUpbitRate() {
  elements.fxRateDisplay.textContent = '업비트 KRW-USDT 환율 조회 중...';
  try {
    const [upbitUsdt] = await Promise.all([
      enabled.upbit
        ? safeFetchJson('https://api.upbit.com/v1/ticker?markets=KRW-USDT')
        : Promise.resolve(null),
    ]);

    usdtKrwRate = parseUpbitPrice(upbitUsdt);
    if (!usdtKrwRate) {
      throw new Error('업비트 가격 파싱 실패');
    }

    elements.fxRateDisplay.textContent = `업비트 KRW-USDT: ${formatNumber(usdtKrwRate, 2)} KRW`;
  } catch (error) {
    usdtKrwRate = 0;
    elements.fxRateDisplay.textContent = `환율 조회 실패: ${normalizeErrorMessage(error)}`;
  }
}

async function safeFetchJson(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    throw new Error(`요청 실패 (${res.status})`);
  }
  return res.json();
}

function parseUpbitPrice(payload) {
  if (!Array.isArray(payload) || !payload.length) {
    return 0;
  }
  return Number(payload[0]?.trade_price || 0);
}

async function analyzeAllGroups(refreshFx = true) {
  if (elements.analyzeAllBtn.disabled) {
    return;
  }

  const groups = [...document.querySelectorAll('.group-card')];
  if (!groups.length) {
    alert('먼저 그룹을 추가해 주세요.');
    return;
  }

  elements.analyzeAllBtn.disabled = true;
  elements.analyzeAllBtn.textContent = '조회 중...';

  try {
    if (refreshFx) {
      await loadUpbitRate();
    }

    for (const groupNode of groups) {
      await analyzeGroup(groupNode);
    }
  } finally {
    elements.analyzeAllBtn.disabled = false;
    elements.analyzeAllBtn.textContent = '전체 조회';
  }
}

async function analyzeGroup(groupNode) {
  const groupResults = groupNode.querySelector('.group-results');
  const totalUsdtEl = groupNode.querySelector('.group-total-usdt');
  const totalKrwEl = groupNode.querySelector('.group-total-krw');
  groupResults.replaceChildren();

  let groupTotalUsdt = 0;
  const rows = [...groupNode.querySelectorAll('.wallet-row')];

  for (const row of rows) {
    const sourceConfig = getSourceConfig(row.querySelector('.source-select').value);
    const address = row.querySelector('.wallet-input').value.trim();
    if (!address) continue;

    const resultWrap = document.createElement('div');
    resultWrap.className = 'wallet-result';
    renderWalletLoading(resultWrap, sourceConfig.label, address);
    groupResults.appendChild(resultWrap);

    try {
      if (!isValidAddress(sourceConfig.chain, address)) {
        throw new Error('주소 형식이 올바르지 않습니다. 체인과 주소를 다시 확인해 주세요.');
      }

      const tokenData = await sourceConfig.fetcher(address);
      const walletUsdt = tokenData.reduce((sum, token) => sum + token.valueUsd, 0);
      groupTotalUsdt += walletUsdt;
      renderWalletResult(resultWrap, tokenData, walletUsdt, sourceConfig.label, address);
    } catch (error) {
      renderWalletError(resultWrap, sourceConfig.label, address, normalizeErrorMessage(error));
    }
  }

  totalUsdtEl.textContent = formatNumber(groupTotalUsdt, 2);
  totalKrwEl.textContent = usdtKrwRate ? formatKrwEok(groupTotalUsdt * usdtKrwRate) : '환율 필요';

  if (!groupResults.children.length) {
    const empty = document.createElement('p');
    empty.className = 'empty-msg';
    empty.textContent = '입력된 지갑 주소가 없습니다.';
    groupResults.appendChild(empty);
  }
}

function normalizeErrorMessage(error) {
  const message = error instanceof Error ? error.message : String(error);
  if (message.includes('Failed to fetch') || message.includes('NetworkError')) {
    return '네트워크/CORS로 API 호출이 차단되었습니다. run_local_server 또는 python 서버로 실행해 주세요.';
  }
  return message;
}

function renderWalletResult(container, tokens, walletUsdt, sourceLabel, address) {
  const header = createWalletHeader(sourceLabel, address);
  if (!tokens.length) {
    const empty = document.createElement('p');
    empty.className = 'empty-msg';
    empty.textContent = '토큰 데이터가 없거나 조회에 실패했습니다.';
    container.replaceChildren(header, empty);
    return;
  }

  const summary = document.createElement('p');
  summary.textContent = '지갑 합계: ';
  const strong = document.createElement('strong');
  strong.textContent = `${formatNumber(walletUsdt, 2)} USDT(USD)`;
  summary.appendChild(strong);
  summary.append(` / ${usdtKrwRate ? formatKrwEok(walletUsdt * usdtKrwRate) : '환율 필요'}`);

  const table = document.createElement('table');
  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');
  ['토큰', '보유량', '가격(USD)', '가치(USD)'].forEach((label) => {
    const th = document.createElement('th');
    th.textContent = label;
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);

  const tbody = document.createElement('tbody');
  tokens
    .sort((a, b) => b.valueUsd - a.valueUsd)
    .forEach((token) => {
      const tr = document.createElement('tr');
      [
        token.symbol,
        formatNumber(token.amount, 6),
        formatNumber(token.priceUsd, 4),
        formatNumber(token.valueUsd, 2),
      ].forEach((value) => {
        const td = document.createElement('td');
        td.textContent = value;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });

  table.append(thead, tbody);
  container.replaceChildren(header, summary, table);
}

function createWalletHeader(sourceLabel, address) {
  const header = document.createElement('h4');
  header.textContent = `${sourceLabel} | ${address}`;
  return header;
}

function renderWalletLoading(container, sourceLabel, address) {
  const status = document.createElement('p');
  status.textContent = '조회 중...';
  container.replaceChildren(createWalletHeader(sourceLabel, address), status);
}

function renderWalletError(container, sourceLabel, address, message) {
  const error = document.createElement('p');
  error.className = 'error';
  error.textContent = `오류: ${message}`;
  container.replaceChildren(createWalletHeader(sourceLabel, address), error);
}

async function fetchEthereumWallet(address) {
  const [ethplorerResult, evmResult] = await Promise.allSettled([
    fetchEthereumWalletFromEthplorer(address),
    fetchEvmWallet(address, '1', 'https://cloudflare-eth.com', 'ethereum', 'ETH'),
  ]);

  const ethplorerTokens = ethplorerResult.status === 'fulfilled' ? ethplorerResult.value : [];
  const evmTokens = evmResult.status === 'fulfilled' ? evmResult.value : [];

  const bySymbol = new Map();
  [...evmTokens, ...ethplorerTokens].forEach((token) => {
    const key = `${token.symbol}|${Number(token.amount).toFixed(8)}`;
    if (!bySymbol.has(key)) bySymbol.set(key, token);
  });

  const merged = [...bySymbol.values()].filter(
    (token) => Number.isFinite(token.amount) && token.amount > 0 && Number.isFinite(token.valueUsd)
  );

  if (!merged.length && ethplorerResult.status === 'rejected' && evmResult.status === 'rejected') {
    throw new Error('Ethereum 조회 실패: API 응답을 확인해 주세요.');
  }

  return merged;
}

async function fetchEthereumWalletFromEthplorer(address) {
  const data = await safeFetchJson(
    `https://api.ethplorer.io/getAddressInfo/${encodeURIComponent(address)}?apiKey=freekey`
  );
  const tokens = data.tokens || [];

  return tokens
    .map(({ tokenInfo, balance }) => {
      const decimals = Number(tokenInfo?.decimals || 0);
      const amount = Number(balance || 0) / 10 ** decimals;
      const priceUsd = Number(tokenInfo?.price?.rate || 0);
      return {
        symbol: tokenInfo?.symbol || tokenInfo?.name || 'UNKNOWN',
        amount,
        priceUsd,
        valueUsd: amount * priceUsd,
      };
    })
    .filter((token) => Number.isFinite(token.amount) && token.amount > 0 && Number.isFinite(token.valueUsd));
}

async function fetchSolanaWallet(address) {
  const [tokenPayload, solPayload] = await Promise.all([
    safeFetchJson(
      `https://api-v2.solscan.io/v2/account/token-accounts?address=${encodeURIComponent(
        address
      )}&page=1&page_size=40&type=token`
    ),
    safeFetchJson('https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd'),
  ]);

  const tokenData = tokenPayload?.data?.tokenAccounts || [];
  const solPriceUsd = Number(solPayload?.solana?.usd || 0);

  return tokenData
    .map((token) => {
      const amount = Number(
        token.amount ?? token.balance ?? token.tokenAmount?.uiAmount ?? token.tokenAmount?.amount ?? 0
      );
      const symbol = token.symbol || token.tokenSymbol || token.tokenName || token.tokenAddress || 'UNKNOWN';
      const priceUsd =
        Number(token.priceUsd ?? token.price_usdt ?? token.tokenPrice?.usd ?? 0) ||
        (symbol === 'SOL' ? solPriceUsd : 0);

      return {
        symbol,
        amount,
        priceUsd: Number(priceUsd || 0),
        valueUsd: amount * Number(priceUsd || 0),
      };
    })
    .filter((token) => Number.isFinite(token.amount) && token.amount > 0 && Number.isFinite(token.valueUsd));
}

async function fetchEvmWallet(address, chainId, rpcUrl, geckoId, symbol) {
  const [explorerResult, nativeResult] = await Promise.allSettled([
    fetchExplorerTokenBalances(chainId, address),
    fetchEvmNativeWallet(address, rpcUrl, geckoId, symbol),
  ]);

  const explorerTokens = explorerResult.status === 'fulfilled' ? explorerResult.value : [];
  const nativeTokens = nativeResult.status === 'fulfilled' ? nativeResult.value : [];

  const merged = [...nativeTokens, ...explorerTokens].filter(
    (token) => Number.isFinite(token.amount) && token.amount > 0 && Number.isFinite(token.valueUsd)
  );

  if (!merged.length) {
    if (explorerResult.status === 'rejected' && nativeResult.status === 'rejected') {
      throw new Error('EVM 조회 실패: RPC/Explorer 응답을 확인해 주세요.');
    }

    return [];
  }

  return merged;
}

async function fetchExplorerTokenBalances(chainId, address) {
  const candidates = [
    `${ETHERSCAN_V2_ENDPOINT}?chainid=${chainId}&module=account&action=addresstokenbalance&address=${encodeURIComponent(
      address
    )}&page=1&offset=200`,
    EXPLORER_V1_ENDPOINTS[chainId]
      ? `${EXPLORER_V1_ENDPOINTS[chainId]}?module=account&action=addresstokenbalance&address=${encodeURIComponent(
          address
        )}&page=1&offset=200`
      : null,
  ].filter(Boolean);

  let rows = [];
  for (const url of candidates) {
    try {
      const payload = await safeFetchJson(url);
      const parsed = parseExplorerRows(payload?.result);
      if (parsed.length) {
        rows = parsed;
        break;
      }
    } catch (error) {
      // try next endpoint
    }
  }

  return rows
    .map((row) => {
      const decimals = Number(row.TokenDivisor || row.tokenDecimal || row.decimals || 0);
      const rawQty = row.TokenQuantity ?? row.balance ?? row.value ?? 0;
      const amount = decimals > 0 ? Number(rawQty) / 10 ** decimals : Number(rawQty || 0);
      const priceUsd = Number(row.TokenPriceUSD || row.tokenPriceUSD || row.usdPrice || 0);

      return {
        symbol: row.TokenSymbol || row.tokenSymbol || row.TokenName || row.tokenName || row.symbol || 'UNKNOWN',
        amount,
        priceUsd,
        valueUsd: amount * priceUsd,
      };
    })
    .filter((token) => Number.isFinite(token.amount) && token.amount > 0 && Number.isFinite(token.valueUsd));
}

function parseExplorerRows(result) {
  if (Array.isArray(result)) return result;
  if (result && Array.isArray(result.items)) return result.items;
  if (typeof result === 'string') {
    try {
      const parsed = JSON.parse(result);
      if (Array.isArray(parsed)) return parsed;
      if (parsed && Array.isArray(parsed.items)) return parsed.items;
    } catch (error) {
      return [];
    }
  }
  return [];
}

async function fetchEvmNativeWallet(address, rpcUrl, geckoId, symbol) {
  const [rpcPayload, pricePayload] = await Promise.all([
    safeFetchJson(rpcUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ jsonrpc: '2.0', method: 'eth_getBalance', params: [address, 'latest'], id: 1 }),
    }),
    safeFetchJson(`https://api.coingecko.com/api/v3/simple/price?ids=${geckoId}&vs_currencies=usd`),
  ]);

  const weiHex = rpcPayload?.result;
  if (!weiHex || typeof weiHex !== 'string') {
    throw new Error('RPC 잔액 조회 실패 (native)');
  }

  const amount = Number(BigInt(weiHex)) / 1e18;
  const priceUsd = Number(pricePayload?.[geckoId]?.usd || 0);

  return [
    {
      symbol,
      amount,
      priceUsd,
      valueUsd: amount * priceUsd,
    },
  ];
}

async function fetchTronWallet(address) {
  const [accPayload, pricePayload] = await Promise.all([
    safeFetchJson(`https://api.trongrid.io/v1/accounts/${encodeURIComponent(address)}`),
    safeFetchJson('https://api.coingecko.com/api/v3/simple/price?ids=tron&vs_currencies=usd'),
  ]);

  const data = accPayload?.data?.[0] || {};
  const amountSun = Number(data.balance || 0);
  const amount = amountSun / 1_000_000;
  const priceUsd = Number(pricePayload?.tron?.usd || 0);

  return [
    {
      symbol: 'TRX',
      amount,
      priceUsd,
      valueUsd: amount * priceUsd,
    },
  ].filter((token) => token.amount > 0 && Number.isFinite(token.valueUsd));
}

async function fetchBitcoinWallet(address) {
  const [addrPayload, pricePayload] = await Promise.all([
    safeFetchJson(`https://blockstream.info/api/address/${encodeURIComponent(address)}`),
    safeFetchJson('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd'),
  ]);

  const funded = Number(addrPayload?.chain_stats?.funded_txo_sum || 0);
  const spent = Number(addrPayload?.chain_stats?.spent_txo_sum || 0);
  const sats = funded - spent;
  const amount = sats / 100_000_000;
  const priceUsd = Number(pricePayload?.bitcoin?.usd || 0);

  return [
    {
      symbol: 'BTC',
      amount,
      priceUsd,
      valueUsd: amount * priceUsd,
    },
  ].filter((token) => token.amount > 0 && Number.isFinite(token.valueUsd));
}

function formatNumber(value, digits = 2) {
  return Number(value || 0).toLocaleString('ko-KR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

function formatKrwEok(krw) {
  const eok = Number(krw || 0) / 100_000_000;
  return `${formatNumber(eok, 2)}억`;
}
