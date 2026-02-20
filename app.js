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
  groupResults.innerHTML = '';

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
    resultWrap.innerHTML = `<h4>${source.toUpperCase()} | ${address}</h4><p>조회 중...</p>`;
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
      resultWrap.innerHTML = `<h4>${source.toUpperCase()} | ${address}</h4><p class="error">오류: ${error.message}</p>`;
    }
  }

  totalUsdtEl.textContent = formatNumber(groupTotalUsdt, 2);
  totalKrwEl.textContent = usdtKrwRate
    ? formatNumber(groupTotalUsdt * usdtKrwRate, 0)
    : '환율 필요';

  if (!groupResults.children.length) {
    groupResults.innerHTML = '<p class="empty-msg">입력된 지갑 주소가 없습니다.</p>';
  }
}

function renderWalletResult(container, tokens, walletUsdt, source, address) {
  if (!tokens.length) {
    container.innerHTML = `<h4>${source.toUpperCase()} | ${address}</h4><p class="empty-msg">토큰 데이터가 없거나 조회에 실패했습니다.</p>`;
    return;
  }

  const rows = tokens
    .sort((a, b) => b.valueUsd - a.valueUsd)
    .map(
      (token) => `
      <tr>
        <td>${token.symbol}</td>
        <td>${formatNumber(token.amount, 6)}</td>
        <td>${formatNumber(token.priceUsd, 4)}</td>
        <td>${formatNumber(token.valueUsd, 2)}</td>
      </tr>
    `
    )
    .join('');

  container.innerHTML = `
    <h4>${source.toUpperCase()} | ${address}</h4>
    <p>지갑 합계: <strong>${formatNumber(walletUsdt, 2)} USDT(USD)</strong> / ${
      usdtKrwRate ? `${formatNumber(walletUsdt * usdtKrwRate, 0)} KRW` : '환율 필요'
    }</p>
    <table>
      <thead>
        <tr><th>토큰</th><th>보유량</th><th>가격(USD)</th><th>가치(USD)</th></tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
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
    fetch(`https://public-api.solscan.io/account/tokens?account=${encodeURIComponent(address)}`),
    fetch('https://api.coingecko.com/api/v3/simple/price?ids=solana&vs_currencies=usd'),
  ]);

  if (!tokenRes.ok) {
    throw new Error(`Solana 조회 실패 (${tokenRes.status})`);
  }

  const tokenData = await tokenRes.json();
  const solPriceUsd = (await priceRes.json())?.solana?.usd ?? 0;

  return tokenData
    .map((token) => {
      const amount = Number(token.tokenAmount?.uiAmount ?? token.tokenAmount?.amount ?? 0);
      const priceUsd = token.tokenPrice?.usd ?? (token.tokenSymbol === 'SOL' ? solPriceUsd : 0);
      const valueUsd = amount * Number(priceUsd || 0);
      return {
        symbol: token.tokenSymbol || token.tokenName || token.tokenAddress || 'UNKNOWN',
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
