const chainAdapters = {
  ethereum: {
    id: 'ethereum',
    displayName: 'Ethereum',
    explorerBaseUrl: 'https://etherscan.io',
    addressPathTemplate: '/address/{address}',
    tokenPathTemplate: '/token/{tokenAddress}',
    validateAddress: (address) => /^0x[a-fA-F0-9]{40}$/.test(address),
    buildExplorerUrl(address) {
      return `${this.explorerBaseUrl}${this.addressPathTemplate.replace('{address}', address)}`;
    },
    async fetchBalances(address, apiKey = '') {
      const keyParam = apiKey ? `&apikey=${apiKey}` : '';
      const base = 'https://api.etherscan.io/api';
      const native = await fetch(`${base}?module=account&action=balance&address=${address}&tag=latest${keyParam}`).then((r) => r.json());
      if (native.status !== '1') throw new Error(native.result || 'ETH 잔액 조회 실패');

      const balances = [{ chainId: 'ethereum', symbol: 'ETH', name: 'Ethereum', amount: Number(native.result) / 1e18, isNative: true, coingeckoId: 'ethereum' }];
      const txs = await fetch(`${base}?module=account&action=tokentx&address=${address}&page=1&offset=100&sort=desc${keyParam}`).then((r) => r.json());
      if (txs.status === '1' && Array.isArray(txs.result)) {
        const tokenMap = new Map();
        for (const tx of txs.result) {
          if (!tx.contractAddress || !tx.tokenSymbol) continue;
          const key = tx.contractAddress.toLowerCase();
          const decimals = Number(tx.tokenDecimal || 0);
          const amount = Number(tx.value || 0) / 10 ** decimals;
          const delta = String(tx.to || '').toLowerCase() === address.toLowerCase() ? amount : -amount;
          const prev = tokenMap.get(key) || 0;
          tokenMap.set(key, Math.max(prev + delta, 0));
          if (tokenMap.size > 40) break;
        }
        for (const [contract, amount] of tokenMap.entries()) {
          const ref = txs.result.find((t) => t.contractAddress.toLowerCase() === contract);
          const symbol = String(ref?.tokenSymbol || '').toUpperCase();
          if (!symbol) continue;
          balances.push({
            chainId: 'ethereum', symbol, name: ref?.tokenName || symbol, amount,
            contractAddress: ref.contractAddress, isNative: false,
            coingeckoId: ({ USDT: 'tether', USDC: 'usd-coin', DAI: 'dai', WETH: 'weth', WBTC: 'wrapped-bitcoin' })[symbol]
          });
        }
      }
      return balances;
    }
  },
  solana: {
    id: 'solana',
    displayName: 'Solana',
    explorerBaseUrl: 'https://solscan.io',
    addressPathTemplate: '/account/{address}',
    tokenPathTemplate: '/token/{tokenAddress}',
    validateAddress: (address) => /^[1-9A-HJ-NP-Za-km-z]{32,44}$/.test(address),
    buildExplorerUrl(address) {
      return `${this.explorerBaseUrl}${this.addressPathTemplate.replace('{address}', address)}`;
    },
    async fetchBalances(address) {
      const rpc = 'https://api.mainnet-beta.solana.com';
      const payload = (method, params) => ({ jsonrpc: '2.0', id: 1, method, params });
      const native = await fetch(rpc, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload('getBalance', [address])) }).then((r) => r.json());
      if (native.error) throw new Error(native.error.message || 'SOL 잔액 조회 실패');
      const result = [{ chainId: 'solana', symbol: 'SOL', name: 'Solana', amount: Number(native.result.value || 0) / 1e9, isNative: true, coingeckoId: 'solana' }];
      const token = await fetch(rpc, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload('getParsedTokenAccountsByOwner', [address, { programId: 'TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA' }, { encoding: 'jsonParsed' }]))
      }).then((r) => r.json());
      for (const item of token?.result?.value || []) {
        const info = item.account?.data?.parsed?.info;
        if (!info) continue;
        const amount = Number(info.tokenAmount?.uiAmount || 0);
        const mint = String(info.mint);
        const symbol = mint.slice(0, 4).toUpperCase();
        result.push({ chainId: 'solana', symbol, name: symbol, amount, contractAddress: mint, isNative: false, coingeckoId: ({ USDT: 'tether', USDC: 'usd-coin' })[symbol] });
      }
      return result;
    }
  }
};

const stateKey = 'wallet-dashboard-static-v2';
const defaultState = {
  groups: [{ id: crypto.randomUUID(), name: '기본 그룹' }],
  wallets: [],
  settings: { hideZeroValue: false, ttlSeconds: 120, coingeckoApiBase: 'https://api.coingecko.com/api/v3', etherscanApiKey: '' }
};
let state = loadState();
let activeGroupId = state.groups[0]?.id || '';
const cache = new Map();

function loadState() {
  try { return { ...defaultState, ...JSON.parse(localStorage.getItem(stateKey) || '{}') }; }
  catch { return structuredClone(defaultState); }
}
function saveState() { localStorage.setItem(stateKey, JSON.stringify(state)); }
function currency(v, c) { return new Intl.NumberFormat('ko-KR', { style: 'currency', currency: c, maximumFractionDigits: c === 'KRW' ? 0 : 2 }).format(v || 0); }
function num(v) { return new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 6 }).format(v || 0); }
function cacheGet(key) { const v = cache.get(key); if (!v || Date.now() > v.exp) return undefined; return v.value; }
function cacheSet(key, value) { cache.set(key, { value, exp: Date.now() + state.settings.ttlSeconds * 1000 }); }

async function fetchPrices(ids) {
  const uniq = [...new Set(ids.filter(Boolean))];
  if (!uniq.length) return {};
  const key = `prices:${uniq.join(',')}`;
  const c = cacheGet(key); if (c) return c;
  const url = `${state.settings.coingeckoApiBase}/simple/price?ids=${encodeURIComponent(uniq.join(','))}&vs_currencies=usd`;
  const data = await fetch(url).then((r) => r.json());
  const out = {}; uniq.forEach((id) => out[id] = Number(data[id]?.usd || 0));
  cacheSet(key, out); return out;
}

async function fetchUsdKrw() {
  const key = 'fx:usdkrw';
  const c = cacheGet(key); if (c) return c;
  try {
    const data = await fetch('https://open.er-api.com/v6/latest/USD').then((r) => r.json());
    const v = Number(data?.rates?.KRW || 1300);
    cacheSet(key, v); return v;
  } catch { return 1300; }
}

async function fetchWalletPortfolio(wallet) {
  const adapter = chainAdapters[wallet.chainId];
  const key = `pf:${wallet.chainId}:${wallet.address}`;
  const c = cacheGet(key); if (c) return c;
  try {
    const assets = await adapter.fetchBalances(wallet.address, state.settings.etherscanApiKey);
    const fallback = { ETH: 'ethereum', SOL: 'solana', USDT: 'tether', USDC: 'usd-coin' };
    const ids = assets.map((a) => a.coingeckoId || fallback[a.symbol] || '').filter(Boolean);
    const [prices, rate] = await Promise.all([fetchPrices(ids), fetchUsdKrw()]);
    const valued = assets.map((a) => {
      const id = a.coingeckoId || fallback[a.symbol] || '';
      const priceUsdt = id ? Number(prices[id] || 0) : 0;
      const valueUsdt = a.amount * priceUsdt;
      return { ...a, priceUsdt, valueUsdt, valueKrw: valueUsdt * rate };
    });
    const pf = {
      wallet,
      assets: valued,
      totalUsdt: valued.reduce((s, a) => s + a.valueUsdt, 0),
      totalKrw: valued.reduce((s, a) => s + a.valueKrw, 0),
      explorerUrl: adapter.buildExplorerUrl(wallet.address),
      error: ''
    };
    cacheSet(key, pf);
    return pf;
  } catch (e) {
    return { wallet, assets: [], totalUsdt: 0, totalKrw: 0, explorerUrl: adapter.buildExplorerUrl(wallet.address), error: e.message || '오류' };
  }
}

function aggregate(portfolios) {
  const map = new Map();
  for (const p of portfolios) for (const a of p.assets) {
    const key = `${a.chainId}:${a.symbol}:${a.contractAddress || 'native'}`;
    const prev = map.get(key) || { ...a };
    if (map.has(key)) { prev.amount += a.amount; prev.valueUsdt += a.valueUsdt; prev.valueKrw += a.valueKrw; }
    map.set(key, prev);
  }
  return Array.from(map.values()).sort((a,b)=>b.valueUsdt-a.valueUsdt);
}

async function render() {
  const app = document.getElementById('app');
  const activeGroup = state.groups.find((g) => g.id === activeGroupId) || state.groups[0];
  activeGroupId = activeGroup?.id || '';
  const wallets = state.wallets.filter((w) => w.groupId === activeGroupId);

  app.innerHTML = `<div class="layout">
    <section class="panel" id="groupPanel"></section>
    <section class="content" style="display:grid;gap:12px">
      <section class="panel" id="addressPanel"></section>
      <section class="panel" id="summaryPanel">로딩 중...</section>
      <section class="panel" id="assetPanel"></section>
      <section class="panel" id="settingsPanel"></section>
      <section class="panel" id="backupPanel"></section>
    </section>
  </div>`;

  renderGroupPanel();
  renderAddressPanel(wallets);
  renderSettingsPanel();
  renderBackupPanel();

  const portfolios = await Promise.all(wallets.map(fetchWalletPortfolio));
  const totalUsdt = portfolios.reduce((s,p)=>s+p.totalUsdt,0);
  const totalKrw = portfolios.reduce((s,p)=>s+p.totalKrw,0);
  renderSummaryPanel(activeGroup, portfolios, totalUsdt, totalKrw);
  renderAssetPanel(aggregate(portfolios));
}

function renderGroupPanel() {
  const el = document.getElementById('groupPanel');
  el.innerHTML = `<h2>GroupList</h2>
    ${state.groups.map(g=>`<div class="group-item ${g.id===activeGroupId?'active':''}">
      <button data-action="select" data-id="${g.id}" class="secondary">${g.name}</button>
      <button data-action="rename" data-id="${g.id}" class="secondary">이름변경</button>
      <button data-action="delete" data-id="${g.id}" class="danger">삭제</button></div>`).join('')}
    <div class="inline"><input id="newGroup" placeholder="새 그룹 이름"/><button id="addGroup">그룹 추가</button></div>`;

  el.onclick = (e) => {
    const t = e.target;
    if (!(t instanceof HTMLElement)) return;
    const id = t.dataset.id;
    const action = t.dataset.action;
    if (action === 'select') { activeGroupId = id; return render(); }
    if (action === 'rename') {
      const name = prompt('새 이름', state.groups.find((g)=>g.id===id)?.name || '');
      if (name) { state.groups = state.groups.map((g)=>g.id===id?{...g,name}:g); saveState(); render(); }
    }
    if (action === 'delete') {
      state.groups = state.groups.filter((g)=>g.id!==id);
      state.wallets = state.wallets.filter((w)=>w.groupId!==id);
      if (!state.groups.length) state.groups = [{ id: crypto.randomUUID(), name: '기본 그룹' }];
      activeGroupId = state.groups[0].id;
      saveState(); render();
    }
  };
  el.querySelector('#addGroup').onclick = () => {
    const i = el.querySelector('#newGroup');
    if (!i.value.trim()) return;
    state.groups.push({ id: crypto.randomUUID(), name: i.value.trim() });
    i.value = ''; saveState(); render();
  };
}

function renderAddressPanel(wallets) {
  const el = document.getElementById('addressPanel');
  el.innerHTML = `<h2>AddressTable</h2>
  <table><thead><tr><th>체인</th><th>별칭</th><th>주소</th><th>USDT</th><th>KRW</th><th>Explorer</th><th></th></tr></thead>
  <tbody>${wallets.map(w=>`<tr><td>${chainAdapters[w.chainId].displayName}</td><td>${w.alias}</td><td class="mono">${w.address}</td><td class="mono">로딩...</td><td class="mono">-</td><td><a class="explorer" target="_blank" rel="noreferrer" href="${chainAdapters[w.chainId].buildExplorerUrl(w.address)}">🔗 View on Explorer</a></td><td><button data-del="${w.id}" class="danger">삭제</button></td></tr>`).join('')}</tbody></table>
  <div class="inline" style="margin-top:10px">
    <select id="chain"><option value="ethereum">Ethereum</option><option value="solana">Solana</option></select>
    <input id="address" class="mono" placeholder="지갑 주소" />
    <input id="alias" placeholder="별칭" />
    <button id="addWallet">주소 추가</button>
  </div><div id="addrErr" class="error"></div>`;

  el.onclick = (e) => {
    const t = e.target;
    if (!(t instanceof HTMLElement)) return;
    if (t.dataset.del) {
      state.wallets = state.wallets.filter((w)=>w.id!==t.dataset.del);
      saveState(); render();
    }
  };

  el.querySelector('#addWallet').onclick = () => {
    const chainId = el.querySelector('#chain').value;
    const address = el.querySelector('#address').value.trim();
    const alias = el.querySelector('#alias').value.trim();
    const err = el.querySelector('#addrErr');
    if (!chainAdapters[chainId].validateAddress(address)) { err.textContent = '주소 형식이 올바르지 않습니다.'; return; }
    state.wallets.push({ id: crypto.randomUUID(), groupId: activeGroupId, chainId, address, alias: alias || address.slice(0,6) });
    saveState(); render();
  };
}

function renderSummaryPanel(group, portfolios, totalUsdt, totalKrw) {
  const tableRows = portfolios.map((p)=>`<tr><td>${chainAdapters[p.wallet.chainId].displayName}</td><td>${p.wallet.alias}</td><td class="mono">${p.wallet.address}</td><td>${p.error?`<span class="badge">부분 실패: ${p.error}</span>`:currency(p.totalUsdt,'USD')}</td><td>${currency(p.totalKrw,'KRW')}</td><td><a class="explorer" target="_blank" rel="noreferrer" href="${p.explorerUrl}">🔗 View on Explorer</a></td></tr>`).join('');
  document.getElementById('summaryPanel').innerHTML = `<h2>GroupPortfolioSummary</h2>
  <div class="summary-grid"><div><b>그룹</b><div>${group?.name || '-'}</div></div><div><b>지갑 수</b><div>${portfolios.length}</div></div>
  <div><b>총액(USDT)</b><div>${currency(totalUsdt,'USD')}</div></div><div><b>총액(KRW)</b><div>${currency(totalKrw,'KRW')}</div></div></div>
  <table style="margin-top:10px"><thead><tr><th>체인</th><th>별칭</th><th>주소</th><th>USDT</th><th>KRW</th><th>Explorer</th></tr></thead><tbody>${tableRows}</tbody></table>`;
}

function renderAssetPanel(assets) {
  const filtered = state.settings.hideZeroValue ? assets.filter((a)=>a.valueUsdt>0) : assets;
  document.getElementById('assetPanel').innerHTML = `<h2>AssetBreakdownTable</h2>
  <table><thead><tr><th>체인</th><th>심볼</th><th>수량</th><th>USDT 단가</th><th>USDT 가치</th><th>KRW 가치</th></tr></thead>
  <tbody>${filtered.map((a)=>`<tr><td>${a.chainId}</td><td>${a.symbol}</td><td>${num(a.amount)}</td><td>${currency(a.priceUsdt,'USD')}</td><td>${currency(a.valueUsdt,'USD')}</td><td>${currency(a.valueKrw,'KRW')}</td></tr>`).join('')}</tbody></table>`;
}

function renderSettingsPanel() {
  const el = document.getElementById('settingsPanel');
  el.innerHTML = `<h2>Settings</h2>
  <label>TTL Cache (초) <input id="ttl" type="number" min="30" value="${state.settings.ttlSeconds}"/></label>
  <label>0가치 토큰 숨김 <input id="hideZero" type="checkbox" ${state.settings.hideZeroValue?'checked':''}/></label>
  <label>CoinGecko API Base <input id="cg" value="${state.settings.coingeckoApiBase}"/></label>
  <label>Etherscan API Key (선택) <input id="ethKey" value="${state.settings.etherscanApiKey || ''}"/></label>
  <button id="saveSettings">설정 저장</button>`;
  el.querySelector('#saveSettings').onclick = () => {
    state.settings.ttlSeconds = Math.max(30, Number(el.querySelector('#ttl').value || 120));
    state.settings.hideZeroValue = Boolean(el.querySelector('#hideZero').checked);
    state.settings.coingeckoApiBase = el.querySelector('#cg').value.trim() || defaultState.settings.coingeckoApiBase;
    state.settings.etherscanApiKey = el.querySelector('#ethKey').value.trim();
    saveState(); render();
  };
}

function renderBackupPanel() {
  const el = document.getElementById('backupPanel');
  el.innerHTML = `<h2>ImportExport</h2><div class="inline">
  <button id="backup">JSON 백업</button>
  <input id="restore" type="file" accept="application/json" />
  </div>`;
  el.querySelector('#backup').onclick = () => {
    const blob = new Blob([JSON.stringify(state, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'portfolio-backup.json'; a.click(); URL.revokeObjectURL(url);
  };
  el.querySelector('#restore').onchange = async (e) => {
    const file = e.target.files?.[0]; if (!file) return;
    const parsed = JSON.parse(await file.text());
    state = { ...defaultState, ...parsed };
    if (!state.groups?.length) state.groups = [{ id: crypto.randomUUID(), name: '기본 그룹' }];
    activeGroupId = state.groups[0].id;
    saveState(); render();
  };
}

render();
