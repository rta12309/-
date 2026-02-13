#!/usr/bin/env python3
"""업비트 공지 파싱 기반 입출금 상태 프록시 서버.

브라우저는 업비트 API를 직접 호출하지 않고 이 서버(/api/*)만 호출한다.
"""

from __future__ import annotations

import re
from typing import Any

import requests
from flask import Flask, jsonify, make_response, request, send_file

UPBIT_NOTICE_URLS = (
    "https://api-manager.upbit.com/api/v1/notices?page=1&per_page=100",
    "https://api-manager.upbit.com/api/v1/notices?page=1&per_page=100&thread_name=notice",
)

app = Flask(__name__)


def with_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return resp


@app.after_request
def apply_cors(resp):
    return with_cors(resp)


@app.errorhandler(Exception)
def handle_uncaught_exception(err):  # noqa: ANN001
    return with_cors(make_response(jsonify({"error": "INTERNAL_SERVER_ERROR", "details": str(err)}), 200))


def _extract_notice_texts(payload: Any) -> list[str]:
    if not isinstance(payload, list):
        return []
    out: list[str] = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        out.append(f"{item.get('title', '')} {item.get('body', '')} {item.get('summary', '')}")
    return out


def _status_from_notices(symbol: str, notice_texts: list[str]) -> dict[str, Any] | None:
    s = symbol.upper()
    deposit: bool | None = None
    withdraw: bool | None = None
    matched: str | None = None

    for text in notice_texts:
        upper = text.upper()
        if not re.search(rf"\b{re.escape(s)}\b", upper):
            continue

        if "입출금" in upper and "중단" in upper:
            deposit, withdraw, matched = False, False, text
            break
        if "입금" in upper and "중단" in upper:
            deposit, matched = False, text
        if "출금" in upper and "중단" in upper:
            withdraw, matched = False, text

        if "입출금" in upper and ("재개" in upper or "정상화" in upper):
            deposit, withdraw, matched = True, True, text
            break
        if "입금" in upper and ("재개" in upper or "정상화" in upper):
            deposit, matched = True, text
        if "출금" in upper and ("재개" in upper or "정상화" in upper):
            withdraw, matched = True, text

    if deposit is None and withdraw is None:
        return None

    return {
        "symbol": s,
        "deposit_enabled": True if deposit is None else deposit,
        "withdraw_enabled": True if withdraw is None else withdraw,
        "source": "업비트공지",
        "matched_notice": matched,
    }


def fetch_upbit_notice_statuses(symbols: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    notice_texts: list[str] = []

    for url in UPBIT_NOTICE_URLS:
        try:
            res = requests.get(url, timeout=10)
            data = res.json()
            extracted = _extract_notice_texts(data)
            if extracted:
                notice_texts = extracted
                break
            warnings.append(f"공지 응답 비어있음: {url}")
        except requests.RequestException as err:
            warnings.append(f"공지 요청 실패({url}): {err}")
        except ValueError:
            warnings.append(f"공지 JSON 파싱 실패({url})")

    if not notice_texts:
        return [], warnings

    statuses: list[dict[str, Any]] = []
    for symbol in symbols:
        st = _status_from_notices(symbol, notice_texts)
        if st:
            statuses.append(st)

    return statuses, warnings


@app.route("/", methods=["GET"])
def index():
    return send_file("upbit_wallet_status_client.html")


@app.route("/health", methods=["GET"])
def health():
    return with_cors(make_response(jsonify({"ok": True}), 200))


@app.route("/api/upbit_wallet_status", methods=["GET", "OPTIONS"])
def upbit_wallet_status():
    if request.method == "OPTIONS":
        return with_cors(make_response("", 200))

    # 선택: ?symbols=BTC,ETH,XRP
    symbols_param = request.args.get("symbols", "")
    symbols = [s.strip().upper() for s in symbols_param.split(",") if s.strip()]
    if not symbols:
        symbols = ["BTC", "ETH", "XRP", "SOL", "FLOW"]

    statuses, warnings = fetch_upbit_notice_statuses(symbols)
    return with_cors(
        make_response(
            jsonify(
                {
                    "ok": True,
                    "data": statuses,
                    "warnings": warnings,
                    "source": "업비트공지파싱",
                }
            ),
            200,
        )
    )


@app.route("/debug/upbit_raw", methods=["GET", "OPTIONS"])
def debug_upbit_raw():
    if request.method == "OPTIONS":
        return with_cors(make_response("", 200))

    payload: list[dict[str, Any]] = []
    errors: list[str] = []
    for url in UPBIT_NOTICE_URLS:
        try:
            res = requests.get(url, timeout=10)
            data = res.json()
            if isinstance(data, list):
                payload = data[:3]
                break
            errors.append(f"응답형식다름: {url}")
        except requests.RequestException as err:
            errors.append(f"요청실패({url}): {err}")
        except ValueError:
            errors.append(f"JSON파싱실패({url})")

    return with_cors(make_response(jsonify({"source": "업비트공지", "sample": payload, "errors": errors}), 200))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
