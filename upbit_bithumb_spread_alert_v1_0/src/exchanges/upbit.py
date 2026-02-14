from dataclasses import dataclass
from typing import Dict, List, Set

from src.core.http import HttpClient


@dataclass
class UpbitAssetStatus:
    symbol: str
    deposit_enabled: bool
    withdraw_enabled: bool
    networks_enabled: Set[str]


class UpbitClient:
    BASE_URL = "https://api.upbit.com"

    def __init__(self, http: HttpClient):
        self.http = http

    def get_krw_symbols(self) -> List[str]:
        data = self.http.get_json(f"{self.BASE_URL}/v1/market/all", params={"isDetails": "false"})
        return [row["market"].split("-")[1].upper() for row in data if str(row.get("market", "")).startswith("KRW-")]

    def get_tickers(self, symbols: List[str]) -> Dict[str, float]:
        if not symbols:
            return {}
        markets = ",".join([f"KRW-{s.upper()}" for s in symbols])
        data = self.http.get_json(f"{self.BASE_URL}/v1/ticker", params={"markets": markets})
        result: Dict[str, float] = {}
        for row in data:
            market = str(row.get("market", ""))
            if not market.startswith("KRW-"):
                continue
            price = row.get("trade_price")
            if price is None:
                continue
            result[market.split("-")[1].upper()] = float(price)
        return result

    def get_asset_status(self) -> Dict[str, UpbitAssetStatus]:
        data = self.http.get_json(f"{self.BASE_URL}/v1/status/wallet")
        result: Dict[str, UpbitAssetStatus] = {}
        for row in data:
            symbol = str(row.get("currency", "")).upper()
            if not symbol:
                continue
            wallet_state = str(row.get("wallet_state", "")).lower()
            block_state = str(row.get("block_state", "")).lower()
            net_type = str(row.get("net_type", "")).upper()

            deposit_enabled = wallet_state in {"working", "deposit_only"} and block_state == "normal"
            withdraw_enabled = wallet_state in {"working", "withdraw_only"} and block_state == "normal"

            current = result.get(symbol)
            if not current:
                current = UpbitAssetStatus(symbol=symbol, deposit_enabled=False, withdraw_enabled=False, networks_enabled=set())
                result[symbol] = current

            current.deposit_enabled = current.deposit_enabled or deposit_enabled
            current.withdraw_enabled = current.withdraw_enabled or withdraw_enabled
            if deposit_enabled and withdraw_enabled and net_type:
                current.networks_enabled.add(net_type)
        return result
