from dataclasses import dataclass


@dataclass
class SpreadResult:
    symbol: str
    upbit_price: float
    bithumb_price: float
    diff_percent: float


def calc_diff_percent(upbit_price: float, bithumb_price: float) -> float:
    if bithumb_price == 0:
        return 0.0
    return ((upbit_price - bithumb_price) / bithumb_price) * 100.0
