import type { AppSettings } from '../types/models';

interface Props {
  settings: AppSettings;
  etherscanApiKey: string;
  onChange: (partial: Partial<AppSettings>) => void;
  onApiKeyChange: (value: string) => void;
}

export const SettingsPanel = ({ settings, etherscanApiKey, onChange, onApiKeyChange }: Props) => (
  <section className="panel">
    <h2>Settings</h2>
    <label>
      TTL Cache (초)
      <input
        type="number"
        min={30}
        value={settings.ttlSeconds}
        onChange={(e) => onChange({ ttlSeconds: Number(e.target.value) || 120 })}
      />
    </label>
    <label>
      0가치 토큰 숨김
      <input
        type="checkbox"
        checked={settings.hideZeroValue}
        onChange={(e) => onChange({ hideZeroValue: e.target.checked })}
      />
    </label>
    <label>
      CoinGecko API Base
      <input value={settings.coingeckoApiBase} onChange={(e) => onChange({ coingeckoApiBase: e.target.value.trim() })} />
    </label>
    <label>
      Etherscan API Key (선택)
      <input value={etherscanApiKey} onChange={(e) => onApiKeyChange(e.target.value.trim())} placeholder="없어도 최소 동작" />
    </label>
  </section>
);
