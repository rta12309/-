const MAX_WALLETS_PER_GROUP = 10;

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
    label: 'BNB Smart Chain (BscScan 링크)',
    chain: 'bsc',
    explorerBase: 'https://bscscan.com/address/',
    apiExample: 'https://api.bscscan.com/api?module=account&action=tokenbalance&address={address}',
    fetcher: null,
  },
  {
    key: 'polygon',
    label: 'Polygon (PolygonScan 링크)',
    chain: 'polygon',
    explorerBase: 'https://polygonscan.com/address/',
    apiExample:
      'https://api.polygonscan.com/api?module=account&action=tokenbalance&address={address}',
    fetcher: null,
  },
  {
    key: 'arbitrum',
    label: 'Arbitrum (Arbiscan 링크)',
    chain: 'arbitrum',
    explorerBase: 'https://arbiscan.io/address/',
    apiExample:
      'https://api.arbiscan.io/api?module=account&action=tokenbalance&address={address}',
    fetcher: null,
  },
  {
    key: 'optimism',
    label: 'Optimism (Optimistic Etherscan 링크)',
    chain: 'optimism',
    explorerBase: 'https://optimistic.etherscan.io/address/',
    apiExample:
      'https://api-optimistic.etherscan.io/api?module=account&action=tokenbalance&address={address}',
    fetcher: null,
  },
  {
    key: 'avalanche',
    label: 'Avalanche (SnowTrace 링크)',
    chain: 'avalanche',
    explorerBase: 'https://snowtrace.io/address/',
    apiExample:
      'https://api.snowtrace.io/api?module=account&action=tokenbalance&address={address}',
    fetcher: null,
  },
  {
    key: 'base',
    label: 'Base (BaseScan 링크)',
    chain: 'base',
    explorerBase: 'https://basescan.org/address/',
    apiExample: 'https://api.basescan.org/api?module=account&action=tokenbalance&address={address}',
    fetcher: null,
  },
  {
    key: 'tron',
    label: 'TRON (Tronscan 링크)',
    chain: 'tron',
    explorerBase: 'https://tronscan.org/#/address/',
    apiExample: 'https://apilist.tronscanapi.com/api/account/tokens?address={address}',
    fetcher: null,
  },
  {
    key: 'bitcoin',
    label: 'Bitcoin (Blockstream 링크)',
    chain: 'bitcoin',
    explorerBase: 'https://blockstream.info/address/',
    apiExample: 'https://blockstream.info/api/address/{address}',
    fetcher: null,
  },
];

let usdtKrwRate = 0;
let elements = null;
let initialized = false;

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
  };

  const required = Object.values(elements).every(Boolean);
  if (!required) {
    console.error('필수 UI 요소를 찾을 수 없습니다.');
    return;
  }

  initialized = true;

  elements.refreshRateBtn.addEventListener('click', loadUpbitRate);
  elements.addGroupBtn.addEventListener('click', () => createGroup());
  elements.analyzeAllBtn.addEventListener('click', analyzeAllGroups);

  createGroup('기본 그룹');

  if (window.location.protocol === 'file:') {
    elements.fxRateDisplay.textContent =
      '파일 직접 실행 모드입니다. 버튼은 동작하지만 환율/온체인 API 조회는 브라우저 CORS 정책으로 차단될 수 있습니다. (권장: python3 -m http.server 4173)';
  } else {
    loadUpbitRate();
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
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
  const apiLink = row.querySelector('.api-link');
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
    const safeAddress = address || '{address}';
    explorerLink.href = `${source.explorerBase}${encodeURIComponent(safeAddress)}`;
    apiLink.href = source.apiExample.replace('{address}', encodeURIComponent(safeAddress));
  };

  sourceSelect.addEventListener('change', updateLinks);
  walletInput.addEventListener('input', updateLinks);
  removeBtn.addEventListener('click', () => row.remove());

  updateLinks();
  return row;
}

function getSourceConfig(key) {
  return SOURCES.find((source) => source.key === key) || SOURCES[0];
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
    elements.fxRateDisplay.textContent = `환율 조회 실패: ${error.message}`;
  }
}

async function safeFetchJson(url) {
  const res = await fetch(url);
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

async function analyzeAllGroups() {
  const groups = [...document.querySelectorAll('.group-card')];
  if (!groups.length) {
    alert('먼저 그룹을 추가해 주세요.');
    return;
  }

  elements.analyzeAllBtn.disabled = true;
  elements.analyzeAllBtn.textContent = '조회 중...';

  try {
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
      if (!sourceConfig.fetcher) {
        throw new Error('현재는 링크 제공만 지원합니다. API 통합은 준비 중입니다.');
      }

      const tokenData = await sourceConfig.fetcher(address);
      const walletUsdt = tokenData.reduce((sum, token) => sum + token.valueUsd, 0);
      groupTotalUsdt += walletUsdt;
      renderWalletResult(resultWrap, tokenData, walletUsdt, sourceConfig.label, address);
    } catch (error) {
      renderWalletError(resultWrap, sourceConfig.label, address, error.message);
    }
  }

  totalUsdtEl.textContent = formatNumber(groupTotalUsdt, 2);
  totalKrwEl.textContent = usdtKrwRate ? formatNumber(groupTotalUsdt * usdtKrwRate, 0) : '환율 필요';

  if (!groupResults.children.length) {
    const empty = document.createElement('p');
    empty.className = 'empty-msg';
    empty.textContent = '입력된 지갑 주소가 없습니다.';
    groupResults.appendChild(empty);
  }
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
  summary.append(` / ${usdtKrwRate ? `${formatNumber(walletUsdt * usdtKrwRate, 0)} KRW` : '환율 필요'}`);

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
  const res = await fetch(
    `https://api.ethplorer.io/getAddressInfo/${encodeURIComponent(address)}?apiKey=freekey`
  );
  if (!res.ok) throw new Error(`Ethereum 조회 실패 (${res.status})`);

  const data = await res.json();
  const tokens = data.tokens || [];

  return tokens
    .map(({ tokenInfo, balance }) => {
      const decimals = Number(tokenInfo.decimals || 0);
      const amount = Number(balance) / 10 ** decimals;
      const priceUsd = Number(tokenInfo.price?.rate || 0);
      return {
        symbol: tokenInfo.symbol || tokenInfo.name || 'UNKNOWN',
        amount,
        priceUsd,
        valueUsd: amount * priceUsd,
      };
    })
    .filter((token) => Number.isFinite(token.amount) && token.amount > 0 && Number.isFinite(token.valueUsd));
}

async function fetchSolanaWallet(address) {
  const [tokenRes, priceRes] = await Promise.all([
    fetch(
      `https://api-v2.solscan.io/v2/account/token-accounts?address=${encodeURIComponent(
        address
      )}&page=1&page_size=40&type=token`
    ),
    fetch('https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd'),
  ]);

  if (!tokenRes.ok) throw new Error(`Solana 조회 실패 (${tokenRes.status})`);

  const tokenPayload = await tokenRes.json();
  const tokenData = tokenPayload?.data?.tokenAccounts || [];
  const solPriceUsd = (await priceRes.json())?.solana?.usd ?? 0;

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

function formatNumber(value, digits = 2) {
  return Number(value || 0).toLocaleString('ko-KR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}
