const MAX_WALLETS_PER_GROUP = 10;

const groupList = document.getElementById('group-list');
const addGroupBtn = document.getElementById('add-group-btn');
const analyzeAllBtn = document.getElementById('analyze-all-btn');
const refreshRateBtn = document.getElementById('refresh-rate-btn');
const fxRateDisplay = document.getElementById('fx-rate-display');

const groupTemplate = document.getElementById('group-template');
const walletTemplate = document.getElementById('wallet-template');

let usdtKrwRate = 0;

refreshRateBtn.addEventListener('click', loadUpbitRate);
addGroupBtn.addEventListener('click', () => createGroup());
analyzeAllBtn.addEventListener('click', analyzeAllGroups);

createGroup('기본 그룹');
loadUpbitRate();

function createGroup(defaultName = '') {
  const node = groupTemplate.content.firstElementChild.cloneNode(true);
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
  groupList.appendChild(node);
}

function createWalletRow() {
  const row = walletTemplate.content.firstElementChild.cloneNode(true);
  const removeBtn = row.querySelector('.remove-wallet-btn');

  removeBtn.addEventListener('click', () => {
    row.remove();
  });

  return row;
}

async function loadUpbitRate() {
  fxRateDisplay.textContent = '업비트 KRW-USDT 환율 조회 중...';
  try {
    const res = await fetch('https://api.upbit.com/v1/ticker?markets=KRW-USDT');
    if (!res.ok) {
      throw new Error('업비트 응답 실패');
    }
    const [ticker] = await res.json();
    usdtKrwRate = ticker.trade_price;
    fxRateDisplay.textContent = `업비트 KRW-USDT: ${formatNumber(usdtKrwRate, 2)} KRW`;
  } catch (error) {
    usdtKrwRate = 0;
    fxRateDisplay.textContent = `환율 조회 실패: ${error.message}`;
  }
}

async function analyzeAllGroups() {
  const groups = [...document.querySelectorAll('.group-card')];
  if (!groups.length) {
    alert('먼저 그룹을 추가해 주세요.');
    return;
  }

  analyzeAllBtn.disabled = true;
  analyzeAllBtn.textContent = '조회 중...';

  try {
    for (const groupNode of groups) {
      await analyzeGroup(groupNode);
    }
  } finally {
    analyzeAllBtn.disabled = false;
    analyzeAllBtn.textContent = '전체 조회';
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
    const source = row.querySelector('.source-select').value;
    const address = row.querySelector('.wallet-input').value.trim();
    if (!address) {
      continue;
    }

    const resultWrap = document.createElement('div');
    resultWrap.className = 'wallet-result';
    renderWalletLoading(resultWrap, source, address);
    groupResults.appendChild(resultWrap);

    try {
      let tokenData;
      if (source === 'etherscan') {
        tokenData = await fetchEthereumWallet(address);
      } else {
        tokenData = await fetchSolanaWallet(address);
      }

      const walletUsdt = tokenData.reduce((sum, t) => sum + t.valueUsd, 0);
      groupTotalUsdt += walletUsdt;
      renderWalletResult(resultWrap, tokenData, walletUsdt, source, address);
    } catch (error) {
      renderWalletError(resultWrap, source, address, error.message);
    }
  }

  totalUsdtEl.textContent = formatNumber(groupTotalUsdt, 2);
  totalKrwEl.textContent = usdtKrwRate
    ? formatNumber(groupTotalUsdt * usdtKrwRate, 0)
    : '환율 필요';

  if (!groupResults.children.length) {
    const empty = document.createElement('p');
    empty.className = 'empty-msg';
    empty.textContent = '입력된 지갑 주소가 없습니다.';
    groupResults.appendChild(empty);
  }
}

function renderWalletResult(container, tokens, walletUsdt, source, address) {
  const header = createWalletHeader(source, address);

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
  summary.append(
    ` / ${usdtKrwRate ? `${formatNumber(walletUsdt * usdtKrwRate, 0)} KRW` : '환율 필요'}`
  );

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

function createWalletHeader(source, address) {
  const header = document.createElement('h4');
  header.textContent = `${source.toUpperCase()} | ${address}`;
  return header;
}

function renderWalletLoading(container, source, address) {
  const status = document.createElement('p');
  status.textContent = '조회 중...';
  container.replaceChildren(createWalletHeader(source, address), status);
}

function renderWalletError(container, source, address, message) {
  const error = document.createElement('p');
  error.className = 'error';
  error.textContent = `오류: ${message}`;
  container.replaceChildren(createWalletHeader(source, address), error);
}

async function fetchEthereumWallet(address) {
  const res = await fetch(
    `https://api.ethplorer.io/getAddressInfo/${encodeURIComponent(address)}?apiKey=freekey`
  );

  if (!res.ok) {
    throw new Error(`Ethereum 조회 실패 (${res.status})`);
  }

  const data = await res.json();
  const tokens = data.tokens || [];

  return tokens
    .map(({ tokenInfo, balance }) => {
      const decimals = Number(tokenInfo.decimals || 0);
      const amount = Number(balance) / 10 ** decimals;
      const priceUsd = Number(tokenInfo.price?.rate || 0);
      const valueUsd = amount * priceUsd;
      return {
        symbol: tokenInfo.symbol || tokenInfo.name || 'UNKNOWN',
        amount,
        priceUsd,
        valueUsd,
      };
    })
    .filter((t) => Number.isFinite(t.amount) && t.amount > 0 && Number.isFinite(t.valueUsd));
}

async function fetchSolanaWallet(address) {
  const [tokenRes, priceRes] = await Promise.all([
    fetch(
      `https://api-v2.solscan.io/v2/account/token-accounts?address=${encodeURIComponent(address)}&page=1&page_size=40&type=token`
    ),
    fetch('https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd'),
  ]);

  if (!tokenRes.ok) {
    throw new Error(`Solana 조회 실패 (${tokenRes.status})`);
  }

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
      const valueUsd = amount * Number(priceUsd || 0);
      return {
        symbol,
        amount,
        priceUsd: Number(priceUsd || 0),
        valueUsd,
      };
    })
    .filter((t) => Number.isFinite(t.amount) && t.amount > 0 && Number.isFinite(t.valueUsd));
}

function formatNumber(value, digits = 2) {
  return Number(value || 0).toLocaleString('ko-KR', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}
