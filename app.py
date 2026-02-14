import argparse
import json
import sys
import time
from datetime import datetime
from urllib.parse import urlencode
from urllib.request import Request, urlopen

UPBIT_MARKETS_URL = "https://api.upbit.com/v1/market/all"
UPBIT_TICKER_URL = "https://api.upbit.com/v1/ticker"
BITHUMB_TICKER_ALL_KRW_URL = "https://api.bithumb.com/public/ticker/ALL_KRW"
USER_AGENT = "upbit-bithumb-gap-alert/1.0"


def beep() -> None:
    """Emit an alert sound if possible."""
    try:
        if sys.platform.startswith("win"):
            import winsound

            winsound.Beep(2000, 700)
        else:
            print("\a", end="", flush=True)
    except Exception:
        pass


def fetch_json(url: str, params: dict[str, str] | None = None) -> dict | list:
    if params:
        url = f"{url}?{urlencode(params)}"

    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def fetch_upbit_krw_tickers() -> dict[str, float]:
    """Return {symbol: trade_price} for all KRW markets on Upbit."""
    markets_data = fetch_json(UPBIT_MARKETS_URL, {"isDetails": "false"})
    krw_markets = [m["market"] for m in markets_data if m["market"].startswith("KRW-")]

    if not krw_markets:
        return {}

    ticker_data = fetch_json(UPBIT_TICKER_URL, {"markets": ",".join(krw_markets)})

    result: dict[str, float] = {}
    for item in ticker_data:
        market = item.get("market", "")
        if market.startswith("KRW-"):
            symbol = market.split("-", 1)[1]
            result[symbol] = float(item["trade_price"])

    return result


def fetch_bithumb_krw_tickers() -> dict[str, float]:
    """Return {symbol: closing_price} for all KRW markets on Bithumb."""
    payload = fetch_json(BITHUMB_TICKER_ALL_KRW_URL)

    if payload.get("status") != "0000":
        raise RuntimeError(f"Bithumb API error: {payload}")

    data = payload.get("data", {})
    result: dict[str, float] = {}

    for symbol, info in data.items():
        if symbol == "date":
            continue
        closing_price = info.get("closing_price")
        if closing_price is None:
            continue
        result[symbol] = float(closing_price)

    return result


def detect_large_gaps(
    upbit_prices: dict[str, float],
    bithumb_prices: dict[str, float],
    threshold_percent: float,
) -> list[tuple[str, float, float, float]]:
    """Return list of (symbol, upbit_price, bithumb_price, percent_gap)."""
    alerts: list[tuple[str, float, float, float]] = []

    common_symbols = sorted(set(upbit_prices) & set(bithumb_prices))
    for symbol in common_symbols:
        upbit_price = upbit_prices[symbol]
        bithumb_price = bithumb_prices[symbol]

        if bithumb_price == 0:
            continue

        gap_percent = abs((upbit_price - bithumb_price) / bithumb_price * 100)
        if gap_percent >= threshold_percent:
            alerts.append((symbol, upbit_price, bithumb_price, gap_percent))

    return alerts


def monitor(threshold: float, interval: int) -> None:
    print(f"모니터링 시작 | 임계값: {threshold:.2f}% | 주기: {interval}초")

    while True:
        try:
            upbit_prices = fetch_upbit_krw_tickers()
            bithumb_prices = fetch_bithumb_krw_tickers()
            alerts = detect_large_gaps(upbit_prices, bithumb_prices, threshold)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if alerts:
                print(f"\n[{timestamp}] ⚠️  {len(alerts)}개 코인에서 가격 차이 발생")
                for symbol, upbit_price, bithumb_price, gap_percent in alerts:
                    print(
                        f" - {symbol:<10} 업비트: {upbit_price:,.2f}원 | "
                        f"빗썸: {bithumb_price:,.2f}원 | 차이: {gap_percent:.2f}%"
                    )
                beep()
            else:
                print(f"[{timestamp}] 정상: {threshold:.2f}% 이상 차이 없음")

        except Exception as exc:
            print(f"[오류] 데이터 조회 실패: {exc}")

        time.sleep(interval)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="업비트와 빗썸의 코인 가격 차이를 감시해 임계값 이상이면 알림을 울립니다."
    )
    parser.add_argument("--threshold", type=float, default=5.0, help="알림 임계값(%) (기본값: 5.0)")
    parser.add_argument("--interval", type=int, default=30, help="조회 주기(초) (기본값: 30)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.threshold < 0:
        raise ValueError("threshold는 0 이상이어야 합니다.")
    if args.interval <= 0:
        raise ValueError("interval은 1 이상이어야 합니다.")

    monitor(threshold=args.threshold, interval=args.interval)


if __name__ == "__main__":
    main()
