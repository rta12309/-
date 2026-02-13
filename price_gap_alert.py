#!/usr/bin/env python3
"""업비트-빗썸 가격 차이(%) 모니터링 알림 앱.

요구사항:
- 두 거래소에 공통 상장된 KRW 마켓 코인만 비교
- 가격 차이가 threshold(기본 5%) 이상이면 알림
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Sequence

UPBIT_TICKER_URL = "https://api.upbit.com/v1/ticker?markets={markets}"
UPBIT_MARKETS_URL = "https://api.upbit.com/v1/market/all?isDetails=false"
BITHUMB_TICKER_URL = "https://api.bithumb.com/public/ticker/ALL_KRW"
DEFAULT_THRESHOLD = 5.0
DEFAULT_INTERVAL = 10


@dataclass(frozen=True)
class GapAlert:
    symbol: str
    upbit_price: float
    bithumb_price: float
    gap_percent: float


def fetch_json(url: str, timeout: int = 10) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": "price-gap-alert/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_upbit_markets() -> List[str]:
    data = fetch_json(UPBIT_MARKETS_URL)
    if not isinstance(data, list):
        raise RuntimeError("업비트 마켓 데이터 형식이 올바르지 않습니다.")

    symbols: List[str] = []
    for item in data:
        market = item.get("market", "")
        if isinstance(market, str) and market.startswith("KRW-"):
            symbols.append(market.split("-", 1)[1])
    return sorted(set(symbols))


def fetch_upbit_prices(symbols: Sequence[str]) -> Dict[str, float]:
    if not symbols:
        return {}

    markets = ",".join(f"KRW-{symbol}" for symbol in symbols)
    data = fetch_json(UPBIT_TICKER_URL.format(markets=markets))
    if not isinstance(data, list):
        raise RuntimeError("업비트 티커 데이터 형식이 올바르지 않습니다.")

    result: Dict[str, float] = {}
    for item in data:
        market = item.get("market", "")
        trade_price = item.get("trade_price")
        if isinstance(market, str) and market.startswith("KRW-") and isinstance(trade_price, (int, float)):
            symbol = market.split("-", 1)[1]
            result[symbol] = float(trade_price)
    return result


def fetch_bithumb_prices() -> Dict[str, float]:
    data = fetch_json(BITHUMB_TICKER_URL)
    if not isinstance(data, dict) or data.get("status") != "0000":
        raise RuntimeError("빗썸 티커 조회에 실패했습니다.")

    payload = data.get("data", {})
    if not isinstance(payload, dict):
        raise RuntimeError("빗썸 티커 데이터 형식이 올바르지 않습니다.")

    result: Dict[str, float] = {}
    for symbol, info in payload.items():
        if symbol == "date" or not isinstance(info, dict):
            continue
        closing_price = info.get("closing_price")
        try:
            result[symbol] = float(closing_price)
        except (TypeError, ValueError):
            continue
    return result


def find_gap_alerts(
    upbit_prices: Dict[str, float],
    bithumb_prices: Dict[str, float],
    threshold: float,
) -> List[GapAlert]:
    alerts: List[GapAlert] = []
    common_symbols = sorted(set(upbit_prices) & set(bithumb_prices))
    for symbol in common_symbols:
        upbit = upbit_prices[symbol]
        bithumb = bithumb_prices[symbol]
        if bithumb <= 0:
            continue
        gap = abs(upbit - bithumb) / bithumb * 100
        if gap >= threshold:
            alerts.append(
                GapAlert(
                    symbol=symbol,
                    upbit_price=upbit,
                    bithumb_price=bithumb,
                    gap_percent=gap,
                )
            )
    alerts.sort(key=lambda item: item.gap_percent, reverse=True)
    return alerts


def beep() -> None:
    sys.stdout.write("\a")
    sys.stdout.flush()


def render_alerts(alerts: Iterable[GapAlert], threshold: float) -> str:
    lines = [f"⚠️  {threshold:.2f}% 이상 가격 차이 감지"]
    for alert in alerts:
        direction = "업비트 > 빗썸" if alert.upbit_price > alert.bithumb_price else "빗썸 > 업비트"
        lines.append(
            (
                f"- {alert.symbol:<10} | 차이 {alert.gap_percent:>6.2f}% "
                f"| 업비트 {alert.upbit_price:>14,.2f} | 빗썸 {alert.bithumb_price:>14,.2f} | {direction}"
            )
        )
    return "\n".join(lines)


def monitor(threshold: float, interval: int, once: bool) -> int:
    try:
        symbols = fetch_upbit_markets()
    except urllib.error.URLError as err:
        print(f"초기화 실패(업비트 마켓 조회): {err}", file=sys.stderr)
        return 1

    if not symbols:
        print("업비트 KRW 마켓을 찾지 못했습니다.", file=sys.stderr)
        return 1

    print(f"모니터링 시작: 공통 코인 탐색 기준 업비트 KRW 마켓 {len(symbols)}개")
    while True:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            upbit_prices = fetch_upbit_prices(symbols)
            bithumb_prices = fetch_bithumb_prices()
            alerts = find_gap_alerts(upbit_prices, bithumb_prices, threshold)
            if alerts:
                beep()
                print(f"\n[{now}]")
                print(render_alerts(alerts, threshold))
            else:
                print(f"[{now}] 이상 없음 (기준 {threshold:.2f}%)")
        except urllib.error.URLError as err:
            print(f"[{now}] 네트워크 오류: {err}", file=sys.stderr)
        except Exception as err:  # noqa: BLE001 - 앱 안정성 위해 루프 유지
            print(f"[{now}] 처리 오류: {err}", file=sys.stderr)

        if once:
            return 0
        time.sleep(interval)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="업비트-빗썸 코인 가격 차이 알림 앱")
    parser.add_argument(
        "--threshold",
        type=float,
        default=DEFAULT_THRESHOLD,
        help=f"알림 기준 퍼센트 (기본값: {DEFAULT_THRESHOLD})",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL,
        help=f"조회 간격(초) (기본값: {DEFAULT_INTERVAL})",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="1회만 조회 후 종료",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.threshold <= 0:
        print("--threshold 는 0보다 커야 합니다.", file=sys.stderr)
        return 2
    if args.interval <= 0:
        print("--interval 은 0보다 커야 합니다.", file=sys.stderr)
        return 2
    return monitor(threshold=args.threshold, interval=args.interval, once=args.once)


if __name__ == "__main__":
    raise SystemExit(main())
