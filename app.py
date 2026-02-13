#!/usr/bin/env python3
"""업비트 입출금 상태 CORS 프록시 서버.

프론트는 업비트 직접 호출 금지:
브라우저 -> /api/upbit_wallet_status -> 서버 -> 업비트
"""

from __future__ import annotations

import os
import uuid
from typing import Any, Tuple

import jwt
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, make_response, request, send_file

load_dotenv()

UPBIT_WALLET_STATUS_URL = "https://api.upbit.com/v1/status/wallet"
UPBIT_ACCESS_KEY = os.getenv("UPBIT_ACCESS_KEY", "").strip()
UPBIT_SECRET_KEY = os.getenv("UPBIT_SECRET_KEY", "").strip()

app = Flask(__name__)


def with_cors(resp):
    """모든 응답에 CORS 헤더를 강제 추가합니다."""
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return resp


@app.after_request
def apply_cors(resp):
    return with_cors(resp)


@app.errorhandler(Exception)
def handle_uncaught_exception(err):  # noqa: ANN001
    """예외가 발생해도 항상 JSON + CORS로 반환합니다."""
    return with_cors(make_response(jsonify({"error": "INTERNAL_SERVER_ERROR", "details": str(err)}), 500))


@app.route("/", methods=["GET"])
def index():
    return send_file("upbit_wallet_status_client.html")


@app.route("/health", methods=["GET"])
def health():
    return with_cors(make_response(jsonify({"ok": True}), 200))


@app.route("/api/upbit_wallet_status", methods=["GET", "OPTIONS"])
def upbit_wallet_status():
    # preflight 명시 처리
    if request.method == "OPTIONS":
        return with_cors(make_response("", 200))

    if not UPBIT_ACCESS_KEY or not UPBIT_SECRET_KEY:
        return with_cors(
            make_response(
                jsonify(
                    {
                        "error": "MISSING_UPBIT_KEYS",
                        "hint": "Add UPBIT_ACCESS_KEY/UPBIT_SECRET_KEY",
                    }
                ),
                200,
            )
        )

    payload = {"access_key": UPBIT_ACCESS_KEY, "nonce": str(uuid.uuid4())}
    token = jwt.encode(payload, UPBIT_SECRET_KEY, algorithm="HS256")
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "upbit-wallet-status-proxy/1.0",
    }

    try:
        res = requests.get(UPBIT_WALLET_STATUS_URL, headers=headers, timeout=10)
        body = safe_json_or_text(res)

        # 어떤 상태코드여도 fetch 실패가 아니라 JSON 응답을 주기 위해 200으로 감싸 전달
        return with_cors(
            make_response(
                jsonify(
                    {
                        "ok": 200 <= res.status_code < 300,
                        "upbit_status_code": res.status_code,
                        "data": body,
                    }
                ),
                200,
            )
        )
    except requests.RequestException as err:
        return with_cors(make_response(jsonify({"error": "UPBIT_REQUEST_FAILED", "details": str(err)}), 200))


@app.route("/debug/upbit_raw", methods=["GET", "OPTIONS"])
def debug_upbit_raw():
    if request.method == "OPTIONS":
        return with_cors(make_response("", 200))

    if not UPBIT_ACCESS_KEY or not UPBIT_SECRET_KEY:
        return with_cors(
            make_response(
                jsonify(
                    {
                        "error": "MISSING_UPBIT_KEYS",
                        "hint": "Add UPBIT_ACCESS_KEY/UPBIT_SECRET_KEY",
                    }
                ),
                200,
            )
        )

    payload = {"access_key": UPBIT_ACCESS_KEY, "nonce": str(uuid.uuid4())}
    token = jwt.encode(payload, UPBIT_SECRET_KEY, algorithm="HS256")
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "upbit-wallet-status-proxy/1.0",
    }

    try:
        res = requests.get(UPBIT_WALLET_STATUS_URL, headers=headers, timeout=10)
        raw_text = res.text[:3000]
        return with_cors(
            make_response(
                jsonify(
                    {
                        "upbit_status_code": res.status_code,
                        "content_type": res.headers.get("Content-Type", ""),
                        "body_preview": raw_text,
                    }
                ),
                200,
            )
        )
    except requests.RequestException as err:
        return with_cors(make_response(jsonify({"error": "UPBIT_REQUEST_FAILED", "details": str(err)}), 200))


def safe_json_or_text(res: requests.Response) -> Any:
    """업비트 응답이 JSON 아니어도 안전하게 반환."""
    try:
        return res.json()
    except ValueError:
        return {"text": res.text[:3000]}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
