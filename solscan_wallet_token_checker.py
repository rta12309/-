#!/usr/bin/env python3
"""Solscan 기반 지갑 토큰 보유량 조회 CLI.

기능:
1) 지갑 주소를 입력받아 Solscan에서 토큰 보유 목록을 조회
2) 보유 토큰 중 티커(symbol) 선택 또는 직접 입력
3) 선택한 토큰의 보유 수량(raw/실수)과 토큰 주소 출력
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal, InvalidOperation

SOLSCAN_ACCOUNT_TOKENS_URL = "https://public-api.solscan.io/account/tokens"
USER_AGENT = "wallet-token-checker/1.0"


class SolscanError(RuntimeError):
    """Solscan API 요청/응답 오류."""


def fetch_wallet_tokens(wallet_address: str) -> list[dict]:
    """주어진 지갑 주소의 SPL 토큰 목록을 Solscan에서 조회한다."""
    query = urllib.parse.urlencode({"account": wallet_address})
    url = f"{SOLSCAN_ACCOUNT_TOKENS_URL}?{query}"
    req = urllib.request.Request(url, headers={"accept": "application/json", "user-agent": USER_AGENT})

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            payload = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise SolscanError(f"Solscan 요청 실패 (HTTP {exc.code})") from exc
    except urllib.error.URLError as exc:
        raise SolscanError("네트워크 오류로 Solscan에 연결할 수 없습니다.") from exc

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SolscanError("Solscan 응답을 JSON으로 파싱할 수 없습니다.") from exc

    if not isinstance(parsed, list):
        raise SolscanError("예상과 다른 Solscan 응답 형식입니다.")

    return parsed


def normalize_amount(raw_amount: str | int | float, decimals: int) -> Decimal:
    """raw amount와 decimals를 받아 사람이 읽기 쉬운 수량을 계산한다."""
    try:
        base = Decimal(str(raw_amount))
        scale = Decimal(10) ** int(decimals)
        return base / scale
    except (InvalidOperation, ValueError):
        return Decimal(0)


def print_token_list(tokens: list[dict]) -> None:
    print("\n[보유 토큰 목록]")
    for idx, token in enumerate(tokens, start=1):
        symbol = token.get("tokenSymbol") or "(티커 없음)"
        token_address = token.get("tokenAddress") or "(주소 없음)"
        amount = normalize_amount(token.get("tokenAmount", {}).get("amount", 0), token.get("tokenAmount", {}).get("decimals", 0))
        print(f"{idx:>2}. {symbol:<12} {amount} (mint: {token_address})")


def find_matching_tokens(tokens: list[dict], user_input: str) -> list[dict]:
    key = user_input.strip().lower()
    matches = []
    for token in tokens:
        symbol = str(token.get("tokenSymbol") or "").lower()
        token_address = str(token.get("tokenAddress") or "").lower()
        if key and (key == symbol or key == token_address):
            matches.append(token)
    return matches


def select_token(tokens: list[dict]) -> dict:
    while True:
        user_input = input("\n확인할 토큰의 번호 / 티커(symbol) / 토큰 주소를 입력하세요: ").strip()

        if user_input.isdigit():
            index = int(user_input)
            if 1 <= index <= len(tokens):
                return tokens[index - 1]
            print("유효한 번호를 입력해주세요.")
            continue

        matches = find_matching_tokens(tokens, user_input)
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            print("같은 티커를 가진 토큰이 여러 개입니다. 번호 또는 토큰 주소로 다시 입력해주세요.")
            for token in matches:
                symbol = token.get("tokenSymbol") or "(티커 없음)"
                token_address = token.get("tokenAddress") or "(주소 없음)"
                print(f"- {symbol} | {token_address}")
            continue

        print("입력과 일치하는 토큰이 없습니다. 번호/티커/주소를 다시 확인해주세요.")


def print_selected_token_holding(token: dict, wallet_address: str) -> None:
    symbol = token.get("tokenSymbol") or "(티커 없음)"
    token_address = token.get("tokenAddress") or "(주소 없음)"
    raw_amount = token.get("tokenAmount", {}).get("amount", 0)
    decimals = token.get("tokenAmount", {}).get("decimals", 0)
    ui_amount = normalize_amount(raw_amount, decimals)

    print("\n[조회 결과]")
    print(f"지갑 주소: {wallet_address}")
    print(f"토큰 티커: {symbol}")
    print(f"토큰 주소: {token_address}")
    print(f"보유 수량(raw): {raw_amount}")
    print(f"보유 수량: {ui_amount}")


def main() -> int:
    print("Solscan 지갑 토큰 보유량 조회기")
    wallet_address = input("조회할 Solana 지갑 주소를 입력하세요: ").strip()

    if not wallet_address:
        print("지갑 주소가 비어 있습니다.")
        return 1

    try:
        tokens = fetch_wallet_tokens(wallet_address)
    except SolscanError as exc:
        print(f"오류: {exc}")
        return 1

    if not tokens:
        print("해당 지갑에서 보유한 SPL 토큰이 없거나 조회되지 않았습니다.")
        return 0

    print_token_list(tokens)
    token = select_token(tokens)
    print_selected_token_holding(token, wallet_address)
    return 0


if __name__ == "__main__":
    sys.exit(main())
