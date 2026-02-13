#!/usr/bin/env python3
"""업비트 입출금 상태 CORS 프록시 서버.

브라우저는 업비트 직접 호출 금지:
브라우저 -> /api/... -> 서버 -> 업비트
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import jwt
import requests
from flask import Flask, jsonify, make_response, request, send_file

UPBIT_WALLET_STATUS_URL = "https://api.upbit.com/v1/status/wallet"
UPBIT_KEY_TEST_URL = "https://api.upbit.com/v1/accounts"  # getMe 대체용 인증 테스트
CONFIG_PATH = Path(__file__).resolve().parent / "config.json"

app = Flask(__name__)


def with_cors(resp):
    """모든 응답에 CORS 헤더를 강제 추가."""
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    return resp


@app.after_request
def apply_cors(resp):
    return with_cors(resp)


@app.errorhandler(Exception)
def handle_uncaught_exception(err):  # noqa: ANN001
    return with_cors(make_response(jsonify({"error": "INTERNAL_SERVER_ERROR", "details": str(err)}), 200))


def load_keys() -> tuple[str, str]:
    """config.json에서 업비트 키를 읽는다."""
    if not CONFIG_PATH.exists():
        return "", ""

    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return "", ""

    access_key = str(data.get("upbit_access_key", "")).strip()
    secret_key = str(data.get("upbit_secret_key", "")).strip()
    return access_key, secret_key


def save_keys(access_key: str, secret_key: str) -> None:
    """config.json에 업비트 키를 저장한다."""
    payload = {
        "upbit_access_key": access_key,
        "upbit_secret_key": secret_key,
    }
    CONFIG_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_auth_headers(access_key: str, secret_key: str) -> dict[str, str]:
    """업비트 JWT Authorization 헤더 생성."""
    jwt_payload = {"access_key": access_key, "nonce": str(uuid.uuid4())}
    token = jwt.encode(jwt_payload, secret_key, algorithm="HS256")
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "upbit-wallet-status-proxy/1.0",
    }


def safe_json_or_text(res: requests.Response) -> Any:
    """업비트 응답이 JSON이 아니어도 안전하게 반환."""
    try:
        return res.json()
    except ValueError:
        return {"text": res.text[:3000]}


def missing_keys_response():
    return with_cors(
        make_response(
            jsonify({"error": "MISSING_UPBIT_KEYS", "hint": "Add UPBIT_ACCESS_KEY/UPBIT_SECRET_KEY"}),
            200,
        )
    )


@app.route("/", methods=["GET"])
def index():
    return send_file("upbit_wallet_status_client.html")


@app.route("/health", methods=["GET"])
def health():
    return with_cors(make_response(jsonify({"ok": True}), 200))


@app.route("/api/upbit_keys", methods=["GET", "POST", "OPTIONS"])
def upbit_keys():
    if request.method == "OPTIONS":
        return with_cors(make_response("", 200))

    if request.method == "GET":
        access_key, secret_key = load_keys()
        return with_cors(
            make_response(
                jsonify(
                    {
                        "has_access_key": bool(access_key),
                        "has_secret_key": bool(secret_key),
                    }
                ),
                200,
            )
        )

    # POST
    payload = request.get_json(silent=True) or {}
    access_key = str(payload.get("access_key", "")).strip()
    secret_key = str(payload.get("secret_key", "")).strip()

    if not access_key or not secret_key:
        return with_cors(make_response(jsonify({"error": "INVALID_KEYS", "hint": "Both keys are required"}), 200))

    save_keys(access_key, secret_key)
    return with_cors(make_response(jsonify({"ok": True, "message": "키 저장 완료"}), 200))


@app.route("/api/upbit_key_test", methods=["GET", "OPTIONS"])
def upbit_key_test():
    if request.method == "OPTIONS":
        return with_cors(make_response("", 200))

    access_key, secret_key = load_keys()
    if not access_key or not secret_key:
        return missing_keys_response()

    headers = build_auth_headers(access_key, secret_key)
    try:
        res = requests.get(UPBIT_KEY_TEST_URL, headers=headers, timeout=10)
        return with_cors(
            make_response(
                jsonify(
                    {
                        "ok": 200 <= res.status_code < 300,
                        "upbit_status_code": res.status_code,
                        "data": safe_json_or_text(res),
                    }
                ),
                200,
            )
        )
    except requests.RequestException as err:
        return with_cors(make_response(jsonify({"error": "UPBIT_REQUEST_FAILED", "details": str(err)}), 200))


@app.route("/api/upbit_wallet_status", methods=["GET", "OPTIONS"])
def upbit_wallet_status():
    if request.method == "OPTIONS":
        return with_cors(make_response("", 200))

    access_key, secret_key = load_keys()
    if not access_key or not secret_key:
        return missing_keys_response()

    headers = build_auth_headers(access_key, secret_key)
    try:
        res = requests.get(UPBIT_WALLET_STATUS_URL, headers=headers, timeout=10)
        return with_cors(
            make_response(
                jsonify(
                    {
                        "ok": 200 <= res.status_code < 300,
                        "upbit_status_code": res.status_code,
                        "data": safe_json_or_text(res),
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

    access_key, secret_key = load_keys()
    if not access_key or not secret_key:
        return missing_keys_response()

    headers = build_auth_headers(access_key, secret_key)
    try:
        res = requests.get(UPBIT_WALLET_STATUS_URL, headers=headers, timeout=10)
        return with_cors(
            make_response(
                jsonify(
                    {
                        "upbit_status_code": res.status_code,
                        "content_type": res.headers.get("Content-Type", ""),
                        "body_preview": res.text[:3000],
                    }
                ),
                200,
            )
        )
    except requests.RequestException as err:
        return with_cors(make_response(jsonify({"error": "UPBIT_REQUEST_FAILED", "details": str(err)}), 200))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
