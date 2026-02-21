#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import sys
import time
from dataclasses import dataclass
from typing import Any, Iterable

import requests


SCAN_CONFIG = {
    "ethereum": {
        "api_base": "https://api.etherscan.io/api",
        "coingecko_platform": "ethereum",
    },
    "bsc": {
        "api_base": "https://api.bscscan.com/api",
        "coingecko_platform": "binance-smart-chain",
    },
    "polygon": {
        "api_base": "https://api.polygonscan.com/api",
        "coingecko_platform": "polygon-pos",
    },
    "arbitrum": {
        "api_base": "https://api.arbiscan.io/api",
        "coingecko_platform": "arbitrum-one",
    },
    "optimism": {
        "api_base": "https://api-optimistic.etherscan.io/api",
        "coingecko_platform": "optimistic-ethereum",
    },
}


@dataclass
class HolderCandidate:
    address: str
    token_amount: float
    usd_value: float


@dataclass
class WalletSignal:
    address: str
    token_amount: float
    usd_value: float
    tx_count_after_since: int
    inbound_ratio: float
    unique_senders: int


class ExplorerClient:
    def __init__(self, api_base: str, api_key: str, sleep_seconds: float = 0.2):
        self.api_base = api_base
        self.api_key = api_key
        self.sleep_seconds = sleep_seconds

    def call(self, **params: Any) -> Any:
        q = {**params, "apikey": self.api_key}
        resp = requests.get(self.api_base, params=q, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        # 일부 체인은 status=0인데 result가 배열로 정상 전달되기도 함
        if status == "0" and data.get("result") in ("", None):
            raise RuntimeError(f"Explorer API error: {data.get('message')} / {data.get('result')}")
        time.sleep(self.sleep_seconds)
        return data.get("result")

    def get_token_holders(self, contract_address: str, max_pages: int, page_size: int) -> list[dict[str, Any]]:
        holders: list[dict[str, Any]] = []
        for page in range(1, max_pages + 1):
            result = self.call(
                module="token",
                action="tokenholderlist",
                contractaddress=contract_address,
                page=page,
                offset=page_size,
            )
            if not result:
                break
            holders.extend(result)
            if len(result) < page_size:
                break
        return holders

    def get_token_tx(self, contract_address: str, address: str, sort: str = "asc", offset: int = 1000) -> list[dict[str, Any]]:
        result = self.call(
            module="account",
            action="tokentx",
            contractaddress=contract_address,
            address=address,
            page=1,
            offset=offset,
            startblock=0,
            endblock=99999999,
            sort=sort,
        )
        return result if isinstance(result, list) else []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="체인scan API로 특정 토큰의 조건부 지갑을 탐지합니다.",
    )
    parser.add_argument("--chain", required=True, choices=sorted(SCAN_CONFIG.keys()), help="대상 체인")
    parser.add_argument("--ticker", required=True, help="티커(예: USDT)")
    parser.add_argument("--scan-api-key", required=True, help="해당 chain scan API 키")
    parser.add_argument(
        "--since",
        required=True,
        help="기준 시각(UTC), 예: 2025-01-01 또는 2025-01-01T12:00:00",
    )
    parser.add_argument("--token-address", help="토큰 컨트랙트 주소(입력 시 티커 탐색 생략)")
    parser.add_argument("--decimals", type=int, default=18, help="홀더 수량이 raw 값일 때 소수점 자리수")
    parser.add_argument(
        "--holder-quantity-is-raw",
        action="store_true",
        default=False,
        help="holder 목록 수량이 raw 정수라면 이 플래그를 켜세요.",
    )
    parser.add_argument("--min-usd", type=float, default=300_000)
    parser.add_argument("--max-usd", type=float, default=30_000_000)
    parser.add_argument("--inbound-ratio-threshold", type=float, default=0.8)
    parser.add_argument("--min-unique-senders", type=int, default=3)
    parser.add_argument("--max-holder-pages", type=int, default=20)
    parser.add_argument("--holder-page-size", type=int, default=100)
    parser.add_argument("--output", default="wallet_signals.csv")
    return parser.parse_args()


def parse_since(value: str) -> int:
    fmt_candidates = ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S"]
    for fmt in fmt_candidates:
        try:
            dt_value = dt.datetime.strptime(value, fmt).replace(tzinfo=dt.timezone.utc)
            return int(dt_value.timestamp())
        except ValueError:
            continue
    raise ValueError("--since 형식이 잘못되었습니다. YYYY-MM-DD 또는 YYYY-MM-DDTHH:MM:SS")


def resolve_token_contract(chain: str, ticker: str) -> str:
    cfg = SCAN_CONFIG[chain]
    platform = cfg["coingecko_platform"]

    coins = requests.get("https://api.coingecko.com/api/v3/coins/list?include_platform=true", timeout=60).json()
    ticker_lower = ticker.lower()
    matches = [c for c in coins if c.get("symbol", "").lower() == ticker_lower and c.get("platforms", {}).get(platform)]
    if not matches:
        raise RuntimeError(f"CoinGecko에서 {chain} 체인의 ticker={ticker} 토큰을 찾지 못했습니다.")

    # 동명이인 심볼이 많아 market_cap 순으로 가장 큰 코인 선택
    best: tuple[str, float] | None = None
    for coin in matches[:30]:
        coin_id = coin["id"]
        detail = requests.get(
            f"https://api.coingecko.com/api/v3/coins/{coin_id}",
            params={"localization": "false", "tickers": "false", "community_data": "false", "developer_data": "false", "sparkline": "false"},
            timeout=30,
        ).json()
        market_cap = float(detail.get("market_data", {}).get("market_cap", {}).get("usd") or 0)
        contract = detail.get("platforms", {}).get(platform)
        if not contract:
            continue
        if best is None or market_cap > best[1]:
            best = (contract, market_cap)
        time.sleep(0.15)

    if best is None:
        raise RuntimeError(f"CoinGecko 후보에서 컨트랙트 주소를 추출하지 못했습니다: ticker={ticker}, chain={chain}")

    return best[0]


def get_token_price_usd(chain: str, contract_address: str) -> float:
    platform = SCAN_CONFIG[chain]["coingecko_platform"]
    data = requests.get(
        f"https://api.coingecko.com/api/v3/simple/token_price/{platform}",
        params={"contract_addresses": contract_address, "vs_currencies": "usd"},
        timeout=30,
    ).json()

    token_data = data.get(contract_address.lower()) or data.get(contract_address)
    if not token_data or "usd" not in token_data:
        raise RuntimeError(f"토큰 USD 가격 조회 실패: {contract_address}")
    return float(token_data["usd"])


def to_amount(quantity_text: str, decimals: int, is_raw: bool) -> float:
    raw = float(quantity_text)
    return raw / (10 ** decimals) if is_raw else raw


def filter_holders_by_usd(
    holders: Iterable[dict[str, Any]],
    token_price_usd: float,
    min_usd: float,
    max_usd: float,
    decimals: int,
    holder_quantity_is_raw: bool,
) -> list[HolderCandidate]:
    out: list[HolderCandidate] = []
    for h in holders:
        address = h.get("TokenHolderAddress") or h.get("address")
        q_text = h.get("TokenHolderQuantity") or h.get("balance")
        if not address or q_text is None:
            continue
        amount = to_amount(str(q_text), decimals, holder_quantity_is_raw)
        usd_value = amount * token_price_usd
        if min_usd <= usd_value <= max_usd:
            out.append(HolderCandidate(address=address, token_amount=amount, usd_value=usd_value))
    return out


def passes_behavior_rules(
    txs: list[dict[str, Any]],
    address: str,
    since_ts: int,
    inbound_ratio_threshold: float,
    min_unique_senders: int,
) -> tuple[bool, int, float, int]:
    if not txs:
        return False, 0, 0.0, 0

    timestamps = [int(t["timeStamp"]) for t in txs if "timeStamp" in t]
    if not timestamps:
        return False, 0, 0.0, 0

    # "특정 시간이후로만" : 해당 토큰 트랜잭션 기준 첫 발생 시점이 since 이후여야 함
    if min(timestamps) < since_ts:
        return False, 0, 0.0, 0

    after = [t for t in txs if int(t.get("timeStamp", 0)) >= since_ts]
    if not after:
        return False, 0, 0.0, 0

    addr_l = address.lower()
    inbound = [t for t in after if str(t.get("to", "")).lower() == addr_l]
    inbound_ratio = len(inbound) / len(after)
    unique_senders = len({str(t.get("from", "")).lower() for t in inbound if t.get("from")})

    ok = inbound_ratio >= inbound_ratio_threshold and unique_senders >= min_unique_senders
    return ok, len(after), inbound_ratio, unique_senders


def write_csv(path: str, signals: list[WalletSignal]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["address", "token_amount", "usd_value", "tx_count_after_since", "inbound_ratio", "unique_senders"])
        for s in signals:
            w.writerow([
                s.address,
                f"{s.token_amount:.8f}",
                f"{s.usd_value:.2f}",
                s.tx_count_after_since,
                f"{s.inbound_ratio:.4f}",
                s.unique_senders,
            ])


def main() -> int:
    args = parse_args()
    since_ts = parse_since(args.since)

    token_address = args.token_address or resolve_token_contract(args.chain, args.ticker)
    print(f"[INFO] token address: {token_address}")

    token_price = get_token_price_usd(args.chain, token_address)
    print(f"[INFO] token price(USD): {token_price}")

    explorer = ExplorerClient(api_base=SCAN_CONFIG[args.chain]["api_base"], api_key=args.scan_api_key)
    holders = explorer.get_token_holders(token_address, args.max_holder_pages, args.holder_page_size)
    print(f"[INFO] fetched holders: {len(holders)}")

    candidates = filter_holders_by_usd(
        holders=holders,
        token_price_usd=token_price,
        min_usd=args.min_usd,
        max_usd=args.max_usd,
        decimals=args.decimals,
        holder_quantity_is_raw=args.holder_quantity_is_raw,
    )
    print(f"[INFO] USD-filtered holders: {len(candidates)}")

    signals: list[WalletSignal] = []
    for i, c in enumerate(candidates, start=1):
        txs = explorer.get_token_tx(token_address, c.address, sort="asc")
        ok, tx_count, inbound_ratio, unique_senders = passes_behavior_rules(
            txs=txs,
            address=c.address,
            since_ts=since_ts,
            inbound_ratio_threshold=args.inbound_ratio_threshold,
            min_unique_senders=args.min_unique_senders,
        )
        if ok:
            signals.append(
                WalletSignal(
                    address=c.address,
                    token_amount=c.token_amount,
                    usd_value=c.usd_value,
                    tx_count_after_since=tx_count,
                    inbound_ratio=inbound_ratio,
                    unique_senders=unique_senders,
                )
            )
        if i % 20 == 0:
            print(f"[INFO] analyzed candidates: {i}/{len(candidates)}")

    write_csv(args.output, signals)
    print(f"[DONE] signals: {len(signals)} -> {args.output}")
    print(json.dumps([s.__dict__ for s in signals], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
