import type { AssetValuation } from '../types/models';
import { formatCurrency, formatNumber } from '../utils/format';

interface Props {
  assets: AssetValuation[];
  hideZeroValue: boolean;
}

export const AssetBreakdownTable = ({ assets, hideZeroValue }: Props) => {
  const filtered = hideZeroValue ? assets.filter((asset) => asset.valueUsdt > 0) : assets;

  return (
    <section className="panel">
      <h2>AssetBreakdownTable</h2>
      <table>
        <thead>
          <tr>
            <th>체인</th>
            <th>심볼</th>
            <th>수량</th>
            <th>단가(USDT)</th>
            <th>가치(USDT)</th>
            <th>가치(KRW)</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((asset) => (
            <tr key={`${asset.chainId}-${asset.symbol}-${asset.contractAddress ?? 'native'}`}>
              <td>{asset.chainId}</td>
              <td>{asset.symbol}</td>
              <td>{formatNumber(asset.amount)}</td>
              <td>{formatCurrency(asset.priceUsdt, 'USD')}</td>
              <td>{formatCurrency(asset.valueUsdt, 'USD')}</td>
              <td>{formatCurrency(asset.valueKrw, 'KRW')}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
};
