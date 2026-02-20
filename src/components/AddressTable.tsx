import type { AddressPortfolio, ChainId, Group, WalletAddress } from '../types/models';
import { supportedChains } from '../adapters/chainAdapters';
import { chainAdapters } from '../adapters/chainAdapters';
import { formatCurrency } from '../utils/format';
import { useState } from 'react';

interface Props {
  group: Group;
  wallets: WalletAddress[];
  portfolios: AddressPortfolio[];
  onAddWallet: (wallet: Omit<WalletAddress, 'id'>) => void;
  onDeleteWallet: (id: string) => void;
}

export const AddressTable = ({ group, wallets, portfolios, onAddWallet, onDeleteWallet }: Props) => {
  const [chainId, setChainId] = useState<ChainId>('ethereum');
  const [address, setAddress] = useState('');
  const [alias, setAlias] = useState('');
  const [error, setError] = useState('');

  const submit = () => {
    const adapter = chainAdapters[chainId];
    if (!adapter.validateAddress(address)) {
      setError('주소 형식이 올바르지 않습니다.');
      return;
    }
    onAddWallet({ groupId: group.id, chainId, address, alias: alias.trim() || address.slice(0, 6) });
    setAddress('');
    setAlias('');
    setError('');
  };

  return (
    <section className="panel">
      <h2>AddressTable</h2>
      <table>
        <thead>
          <tr>
            <th>체인</th>
            <th>별칭</th>
            <th>지갑 주소</th>
            <th>총액(USDT)</th>
            <th>총액(KRW)</th>
            <th>Explorer</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {wallets.map((wallet) => {
            const portfolio = portfolios.find((p) => p.wallet.id === wallet.id);
            return (
              <tr key={wallet.id}>
                <td>{chainAdapters[wallet.chainId].definition.displayName}</td>
                <td>{wallet.alias}</td>
                <td className="mono">{wallet.address}</td>
                <td>{portfolio?.error ? `부분 실패: ${portfolio.error}` : formatCurrency(portfolio?.totalUsdt ?? 0, 'USD')}</td>
                <td>{formatCurrency(portfolio?.totalKrw ?? 0, 'KRW')}</td>
                <td>
                  <a href={portfolio?.explorerUrl ?? chainAdapters[wallet.chainId].buildExplorerUrl(wallet.address)} target="_blank" rel="noreferrer" className="explorer-btn">🔗 View on Explorer</a>
                </td>
                <td><button onClick={() => onDeleteWallet(wallet.id)}>삭제</button></td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <div className="address-form">
        <select value={chainId} onChange={(e) => setChainId(e.target.value as ChainId)}>
          {supportedChains.map((chain) => <option key={chain.id} value={chain.id}>{chain.displayName}</option>)}
        </select>
        <input value={address} onChange={(e) => setAddress(e.target.value.trim())} placeholder="지갑 주소" className="mono" />
        <input value={alias} onChange={(e) => setAlias(e.target.value)} placeholder="별칭" />
        <button onClick={submit}>주소 추가</button>
      </div>
      {error && <p className="error">{error}</p>}
    </section>
  );
};
