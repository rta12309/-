from dataclasses import dataclass
from typing import Dict, List

from src.core.http import HttpClient


@dataclass
class BithumbAssetStatus:
    symbol: str
    deposit_enabled: bool
    withdraw_enabled: bool


class BithumbClient:
    BASE_URL = "https://api.bithumb.com"

    def __init__(self, http: HttpClient):
        self.http = http

    def get_tickers(self) -> Dict[str, float]:
        data = self.http.get_json(f"{self.BASE_URL}/public/ticker/ALL_KRW")
        payload = data.get("data", {}) if isinstance(data, dict) else {}
        result: Dict[str, float] = {}
        for symbol, row in payload.items():
            if symbol == "date":
                continue
            try:
                result[symbol.upper()] = float(row.get("closing_price", 0))
            except Exception:
                continue
        return result

    def get_krw_symbols(self) -> List[str]:
        return list(self.get_tickers().keys())

    def get_asset_status(self) -> Dict[str, BithumbAssetStatus]:
        # 공개 API 기준 코인 단위 입출금 상태 제공. 네트워크별 상태는 제한적.
        data = self.http.get_json(f"{self.BASE_URL}/public/assetsstatus/ALL")
        payload = data.get("data", {}) if isinstance(data, dict) else {}
        result: Dict[str, BithumbAssetStatus] = {}
        for symbol, row in payload.items():
            if symbol == "date":
                continue
            deposit = str(row.get("deposit_status", "0")) == "1"
            withdraw = str(row.get("withdrawal_status", "0")) == "1"
            result[symbol.upper()] = BithumbAssetStatus(symbol=symbol.upper(), deposit_enabled=deposit, withdraw_enabled=withdraw)
        return result
