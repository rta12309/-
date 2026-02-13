#!/usr/bin/env python3
"""업비트-빗썸 가격 차이(%) 모니터링 알림 앱.

요구사항:
- 두 거래소에 공통 상장된 KRW 마켓 코인만 비교
- 가격 차이가 threshold(기본 5%) 이상이면 알림
- 입출금 제한 코인은 별도 표시하고 알림 제외
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime
from itertools import islice
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

UPBIT_TICKER_URL = "https://api.upbit.com/v1/ticker?markets={markets}"
UPBIT_MARKETS_URL = "https://api.upbit.com/v1/market/all?isDetails=false"
UPBIT_WALLET_STATUS_URLS = (
    "https://api.upbit.com/v1/status/wallet",
    "https://sg-api.upbit.com/v1/status/wallet",
    "https://id-api.upbit.com/v1/status/wallet",
    "https://th-api.upbit.com/v1/status/wallet",
)
BITHUMB_TICKER_URL = "https://api.bithumb.com/public/ticker/ALL_KRW"
BITHUMB_ASSET_STATUS_URL = "https://api.bithumb.com/public/assetsstatus/ALL"
THEDDARI_SYMBOL_URL = "https://theddari.com/crypto/{symbol}"
DEFAULT_THRESHOLD = 5.0
DEFAULT_INTERVAL = 10
UPBIT_TICKER_BATCH_SIZE = 100  # Upbit ticker endpoint limit


@dataclass(frozen=True)
class GapAlert:
    symbol: str
    upbit_price: float
    bithumb_price: float
    gap_percent: float


@dataclass(frozen=True)
class TransferStatus:
    deposit_enabled: bool
    withdraw_enabled: bool


@dataclass(frozen=True)
class RestrictedCoin:
    symbol: str
    upbit: TransferStatus
    bithumb: TransferStatus


def fetch_json(url: str, timeout: int = 10) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": "price-gap-alert/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_text(url: str, timeout: int = 10) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 price-gap-alert/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="ignore")


def chunked(items: Sequence[str], size: int) -> Iterator[List[str]]:
    iterator = iter(items)
    while True:
        batch = list(islice(iterator, size))
        if not batch:
            break
        yield batch


def fetch_upbit_markets() -> List[str]:
    data = fetch_json(UPBIT_MARKETS_URL)
    if not isinstance(data, list):
        raise RuntimeError("업비트 마켓 데이터 형식이 올바르지 않습니다.")

    symbols: List[str] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        market = item.get("market", "")
        if isinstance(market, str) and market.startswith("KRW-"):
            symbols.append(market.split("-", 1)[1])
    return sorted(set(symbols))


def fetch_upbit_prices(symbols: Sequence[str]) -> Dict[str, float]:
    if not symbols:
        return {}

    result: Dict[str, float] = {}
    for batch in chunked(symbols, UPBIT_TICKER_BATCH_SIZE):
        markets = ",".join(f"KRW-{symbol}" for symbol in batch)
        data = fetch_json(UPBIT_TICKER_URL.format(markets=markets))
        if not isinstance(data, list):
            raise RuntimeError("업비트 티커 데이터 형식이 올바르지 않습니다.")

        for item in data:
            if not isinstance(item, dict):
                continue
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


def to_bool_flag(value: object) -> bool:
    text = str(value).strip().lower()
    return text in {"1", "true", "y", "yes", "working", "normal", "available"}


def fetch_upbit_transfer_statuses() -> Dict[str, TransferStatus]:
    last_error: Optional[str] = None

    for url in UPBIT_WALLET_STATUS_URLS:
        try:
            data = fetch_json(url)
        except Exception as err:  # noqa: BLE001
            last_error = f"{url}: {err}"
            continue

        if isinstance(data, dict) and data.get("error"):
            last_error = f"{url}: {data.get('error')}"
            continue

        if not isinstance(data, list):
            last_error = f"{url}: 업비트 입출금 상태 데이터 형식이 올바르지 않습니다."
            continue

        statuses: Dict[str, TransferStatus] = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            symbol = item.get("currency")
            wallet_state = item.get("wallet_state")
            block_state = item.get("block_state")
            if not isinstance(symbol, str):
                continue

            deposit_enabled = str(wallet_state).lower() == "working"
            withdraw_enabled = str(block_state).lower() == "normal"
            statuses[symbol.upper()] = TransferStatus(
                deposit_enabled=deposit_enabled,
                withdraw_enabled=withdraw_enabled,
            )

        if statuses:
            return statuses
        last_error = f"{url}: 업비트 입출금 상태 응답이 비어 있습니다."

    raise RuntimeError(f"업비트 입출금 상태 조회에 실패했습니다. {last_error or ''}".strip())


def fetch_bithumb_transfer_statuses() -> Dict[str, TransferStatus]:
    data = fetch_json(BITHUMB_ASSET_STATUS_URL)
    if not isinstance(data, dict) or data.get("status") != "0000":
        raise RuntimeError("빗썸 입출금 상태 조회에 실패했습니다.")

    payload = data.get("data", {})
    if not isinstance(payload, dict):
        raise RuntimeError("빗썸 입출금 상태 데이터 형식이 올바르지 않습니다.")

    statuses: Dict[str, TransferStatus] = {}
    for symbol, info in payload.items():
        if not isinstance(symbol, str) or not isinstance(info, dict):
            continue

        deposit_raw = info.get("deposit_status", info.get("deposit", info.get("depositState", "")))
        withdraw_raw = info.get("withdrawal_status", info.get("withdrawal", info.get("withdrawState", "")))

        statuses[symbol.upper()] = TransferStatus(
            deposit_enabled=to_bool_flag(deposit_raw),
            withdraw_enabled=to_bool_flag(withdraw_raw),
        )
    return statuses




def fetch_transfer_statuses_safe() -> Tuple[Optional[Dict[str, TransferStatus]], Optional[Dict[str, TransferStatus]], List[str]]:
    return fetch_transfer_statuses_with_fallback([])[:3]


def _extract_flag_near(text: str, key: str) -> Optional[bool]:
    key_group = f"(?:{key})"
    patterns = [
        rf"{key_group}\s*[:：\-]?\s*(?P<state>가능|불가|점검|중지|정상|working|normal|suspend(?:ed)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        token = str(match.group("state")).lower()
        if token in {"가능", "정상", "working", "normal"}:
            return True
        if token in {"불가", "점검", "중지", "suspend", "suspended"}:
            return False
    return None


def _extract_exchange_status(section: str) -> Optional[TransferStatus]:
    deposit = _extract_flag_near(section, "입금|deposit")
    withdraw = _extract_flag_near(section, "출금|withdraw")
    if deposit is None or withdraw is None:
        return None
    return TransferStatus(deposit_enabled=deposit, withdraw_enabled=withdraw)


def parse_theddari_statuses_from_html(raw_html: str) -> Tuple[Optional[TransferStatus], Optional[TransferStatus]]:
    normalized = re.sub(r"\s+", " ", html.unescape(raw_html))

    def section_around(keyword: str) -> str:
        idx = normalized.find(keyword)
        if idx < 0:
            return ""
        start = idx
        end = min(len(normalized), idx + 360)
        return normalized[start:end]

    upbit_status = _extract_exchange_status(section_around("업비트"))
    bithumb_status = _extract_exchange_status(section_around("빗썸"))
    return upbit_status, bithumb_status


def fetch_theddari_transfer_statuses(symbols: Sequence[str]) -> Tuple[Dict[str, TransferStatus], Dict[str, TransferStatus], List[str]]:
    upbit_statuses: Dict[str, TransferStatus] = {}
    bithumb_statuses: Dict[str, TransferStatus] = {}
    warnings: List[str] = []

    for symbol in symbols:
        upper = symbol.upper()
        url = THEDDARI_SYMBOL_URL.format(symbol=upper)
        try:
            raw_html = fetch_text(url)
            upbit_status, bithumb_status = parse_theddari_statuses_from_html(raw_html)
            if upbit_status:
                upbit_statuses[upper] = upbit_status
            if bithumb_status:
                bithumb_statuses[upper] = bithumb_status
            if not upbit_status and not bithumb_status:
                warnings.append(f"더따리 크롤링 파싱 실패: {upper}")
        except Exception as err:  # noqa: BLE001
            warnings.append(f"더따리 크롤링 실패({upper}): {err}")

    return upbit_statuses, bithumb_statuses, warnings


def fetch_transfer_statuses_with_fallback(
    symbols: Sequence[str],
) -> Tuple[
    Optional[Dict[str, TransferStatus]],
    Optional[Dict[str, TransferStatus]],
    List[str],
    Dict[str, str],
    Dict[str, str],
]:
    warnings: List[str] = []
    upbit_statuses: Optional[Dict[str, TransferStatus]] = None
    bithumb_statuses: Optional[Dict[str, TransferStatus]] = None
    upbit_sources: Dict[str, str] = {}
    bithumb_sources: Dict[str, str] = {}

    try:
        upbit_statuses = fetch_upbit_transfer_statuses()
        upbit_sources.update({symbol: "공식API" for symbol in upbit_statuses})
    except Exception as err:  # noqa: BLE001
        warnings.append(f"업비트 입출금 상태 조회 실패: {err}")

    try:
        bithumb_statuses = fetch_bithumb_transfer_statuses()
        bithumb_sources.update({symbol: "공식API" for symbol in bithumb_statuses})
    except Exception as err:  # noqa: BLE001
        warnings.append(f"빗썸 입출금 상태 조회 실패: {err}")

    unresolved_symbols = [
        s.upper()
        for s in symbols
        if (upbit_statuses is None or s.upper() not in upbit_statuses)
        or (bithumb_statuses is None or s.upper() not in bithumb_statuses)
    ]
    if unresolved_symbols:
        c_up, c_bi, c_warnings = fetch_theddari_transfer_statuses(unresolved_symbols)
        warnings.extend(c_warnings)
        if c_up:
            if upbit_statuses is None:
                upbit_statuses = {}
            for symbol, status in c_up.items():
                if symbol not in upbit_statuses:
                    upbit_statuses[symbol] = status
                    upbit_sources[symbol] = "더따리크롤링"
        if c_bi:
            if bithumb_statuses is None:
                bithumb_statuses = {}
            for symbol, status in c_bi.items():
                if symbol not in bithumb_statuses:
                    bithumb_statuses[symbol] = status
                    bithumb_sources[symbol] = "더따리크롤링"

    return upbit_statuses, bithumb_statuses, warnings, upbit_sources, bithumb_sources

def filter_restricted_coins(
    symbols: Sequence[str],
    upbit_statuses: Optional[Dict[str, TransferStatus]],
    bithumb_statuses: Optional[Dict[str, TransferStatus]],
) -> Tuple[List[str], List[RestrictedCoin]]:
    tradable: List[str] = []
    restricted: List[RestrictedCoin] = []

    if upbit_statuses is None or bithumb_statuses is None:
        return list(symbols), []

    default_status = TransferStatus(deposit_enabled=False, withdraw_enabled=False)
    for symbol in symbols:
        upbit = upbit_statuses.get(symbol, default_status)
        bithumb = bithumb_statuses.get(symbol, default_status)
        enabled_all = all(
            [
                upbit.deposit_enabled,
                upbit.withdraw_enabled,
                bithumb.deposit_enabled,
                bithumb.withdraw_enabled,
            ]
        )
        if enabled_all:
            tradable.append(symbol)
        else:
            restricted.append(RestrictedCoin(symbol=symbol, upbit=upbit, bithumb=bithumb))
    return tradable, restricted


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


def status_text(status: TransferStatus) -> str:
    deposit = "입금가능" if status.deposit_enabled else "입금불가"
    withdraw = "출금가능" if status.withdraw_enabled else "출금불가"
    return f"{deposit}/{withdraw}"


def status_value_text(value: Optional[bool]) -> str:
    if value is None:
        return "확인불가"
    return "가능" if value else "불가"


def symbol_status_line(
    symbol: str,
    upbit_statuses: Optional[Dict[str, TransferStatus]],
    bithumb_statuses: Optional[Dict[str, TransferStatus]],
    upbit_sources: Optional[Dict[str, str]] = None,
    bithumb_sources: Optional[Dict[str, str]] = None,
) -> str:
    up = upbit_statuses.get(symbol) if upbit_statuses else None
    bi = bithumb_statuses.get(symbol) if bithumb_statuses else None

    up_deposit = status_value_text(None if up is None else up.deposit_enabled)
    up_withdraw = status_value_text(None if up is None else up.withdraw_enabled)
    bi_deposit = status_value_text(None if bi is None else bi.deposit_enabled)
    bi_withdraw = status_value_text(None if bi is None else bi.withdraw_enabled)
    up_source = (upbit_sources or {}).get(symbol, "-")
    bi_source = (bithumb_sources or {}).get(symbol, "-")

    return (
        f"상태 | {symbol:<10} | 업비트 입금:{up_deposit}/출금:{up_withdraw} "
        f"(출처:{up_source}) | 빗썸 입금:{bi_deposit}/출금:{bi_withdraw} (출처:{bi_source})"
    )


def render_alert_statuses(
    alerts: Sequence[GapAlert],
    upbit_statuses: Optional[Dict[str, TransferStatus]],
    bithumb_statuses: Optional[Dict[str, TransferStatus]],
    upbit_sources: Optional[Dict[str, str]] = None,
    bithumb_sources: Optional[Dict[str, str]] = None,
) -> str:
    if not alerts:
        return ""
    return "\n".join(
        symbol_status_line(a.symbol, upbit_statuses, bithumb_statuses, upbit_sources, bithumb_sources)
        for a in alerts
    )


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


def render_restricted_coins(restricted: Sequence[RestrictedCoin], limit: int = 20) -> str:
    if not restricted:
        return ""

    lines = [f"🚫 입출금 제한 코인 {len(restricted)}개 (알림 제외)"]
    for item in restricted[:limit]:
        lines.append(
            f"- {item.symbol:<10} | 업비트 {status_text(item.upbit)} | 빗썸 {status_text(item.bithumb)}"
        )
    if len(restricted) > limit:
        lines.append(f"... 외 {len(restricted) - limit}개")
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

    print(f"모니터링 시작: 업비트 KRW 마켓 {len(symbols)}개")
    while True:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        had_error = False
        try:
            upbit_prices = fetch_upbit_prices(symbols)
            bithumb_prices = fetch_bithumb_prices()
            upbit_statuses, bithumb_statuses, status_warnings, upbit_sources, bithumb_sources = (
                fetch_transfer_statuses_with_fallback(sorted(set(upbit_prices) & set(bithumb_prices)))
            )

            common_symbols = sorted(set(upbit_prices) & set(bithumb_prices))
            tradable_symbols, restricted = filter_restricted_coins(common_symbols, upbit_statuses, bithumb_statuses)

            for warning in status_warnings:
                print(f"[{now}] 경고: {warning}", file=sys.stderr)

            filtered_upbit = {s: upbit_prices[s] for s in tradable_symbols if s in upbit_prices}
            filtered_bithumb = {s: bithumb_prices[s] for s in tradable_symbols if s in bithumb_prices}

            alerts = find_gap_alerts(filtered_upbit, filtered_bithumb, threshold)
            print(f"[{now}] 공통코인 {len(common_symbols)}개 / 알림대상 {len(tradable_symbols)}개")

            restricted_msg = render_restricted_coins(restricted)
            if restricted_msg:
                print(restricted_msg)

            if alerts:
                beep()
                print(render_alerts(alerts, threshold))
                print(render_alert_statuses(alerts, upbit_statuses, bithumb_statuses, upbit_sources, bithumb_sources))
            else:
                print(f"[{now}] 이상 없음 (기준 {threshold:.2f}%)")
        except urllib.error.URLError as err:
            had_error = True
            print(f"[{now}] 네트워크 오류: {err}", file=sys.stderr)
        except Exception as err:  # noqa: BLE001 - 앱 안정성 위해 루프 유지
            had_error = True
            print(f"[{now}] 처리 오류: {err}", file=sys.stderr)

        if once:
            return 1 if had_error else 0
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
