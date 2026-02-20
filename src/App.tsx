import { useEffect, useMemo, useState } from 'react';
import { AddressTable } from './components/AddressTable';
import { AssetBreakdownTable } from './components/AssetBreakdownTable';
import { GroupList } from './components/GroupList';
import { GroupPortfolioSummary } from './components/GroupPortfolioSummary';
import { ImportExportPanel } from './components/ImportExportPanel';
import { SettingsPanel } from './components/SettingsPanel';
import { aggregateGroupPortfolio, fetchAddressPortfolio } from './services/portfolioService';
import { useAppStore } from './store';
import type { AddressPortfolio } from './types/models';

function App() {
  const {
    groups,
    wallets,
    settings,
    etherscanApiKey,
    addGroup,
    renameGroup,
    deleteGroup,
    addWallet,
    removeWallet,
    setSettings,
    setEtherscanApiKey,
    importData
  } = useAppStore();
  const [activeGroupId, setActiveGroupId] = useState(groups[0]?.id ?? '');
  const [portfolios, setPortfolios] = useState<AddressPortfolio[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!groups.find((group) => group.id === activeGroupId)) {
      setActiveGroupId(groups[0]?.id ?? '');
    }
  }, [activeGroupId, groups]);

  useEffect(() => {
    const run = async () => {
      setLoading(true);
      const fetched = await Promise.all(wallets.map((wallet) => fetchAddressPortfolio(wallet, settings, etherscanApiKey)));
      setPortfolios(fetched);
      setLoading(false);
    };

    run();
  }, [wallets, settings, etherscanApiKey]);

  const activeGroup = groups.find((group) => group.id === activeGroupId) ?? null;
  const activeWallets = wallets.filter((wallet) => wallet.groupId === activeGroupId);
  const activePortfolios = portfolios.filter((portfolio) => portfolio.wallet.groupId === activeGroupId);

  const groupPortfolio = useMemo(
    () => (activeGroup ? aggregateGroupPortfolio(activeGroup, activePortfolios) : null),
    [activeGroup, activePortfolios]
  );

  return (
    <main className="app">
      <header>
        <h1>멀티체인 지갑 포트폴리오 대시보드</h1>
        <p>주소 조회 전용 앱 (프라이빗키/시드 미요구)</p>
      </header>

      <div className="layout">
        <GroupList
          groups={groups}
          activeGroupId={activeGroupId}
          onSelect={setActiveGroupId}
          onAdd={addGroup}
          onRename={renameGroup}
          onDelete={deleteGroup}
        />

        <section className="content">
          {activeGroup && (
            <AddressTable
              group={activeGroup}
              wallets={activeWallets}
              portfolios={activePortfolios}
              onAddWallet={addWallet}
              onDeleteWallet={removeWallet}
            />
          )}
          {loading && <p>데이터를 불러오는 중...</p>}
          <GroupPortfolioSummary portfolio={groupPortfolio} />
          <AssetBreakdownTable assets={groupPortfolio?.aggregatedAssets ?? []} hideZeroValue={settings.hideZeroValue} />
          <SettingsPanel
            settings={settings}
            etherscanApiKey={etherscanApiKey}
            onChange={setSettings}
            onApiKeyChange={setEtherscanApiKey}
          />
          <ImportExportPanel payload={{ groups, wallets, settings }} onImport={importData} />
        </section>
      </div>
    </main>
  );
}

export default App;
