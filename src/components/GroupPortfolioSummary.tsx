import type { GroupPortfolio } from '../types/models';
import { formatCurrency } from '../utils/format';

export const GroupPortfolioSummary = ({ portfolio }: { portfolio: GroupPortfolio | null }) => {
  if (!portfolio) return null;
  return (
    <section className="panel summary">
      <h2>GroupPortfolioSummary</h2>
      <p><strong>그룹:</strong> {portfolio.group.name}</p>
      <p><strong>지갑 수:</strong> {portfolio.addresses.length}</p>
      <p><strong>총액(USDT):</strong> {formatCurrency(portfolio.totalUsdt, 'USD')}</p>
      <p><strong>총액(KRW):</strong> {formatCurrency(portfolio.totalKrw, 'KRW')}</p>
    </section>
  );
};
