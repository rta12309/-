#!/usr/bin/env python3
"""업비트 입출금 상태 CORS 우회용 Flask 서버.

구조:
브라우저(프론트) -> 이 서버(/api/upbit_wallet_status) -> 업비트 API
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from flask import Flask, Response, jsonify, send_file

UPBIT_WALLET_STATUS_URL = "https://api.upbit.com/v1/status/wallet"
BASE_DIR = Path(__file__).resolve().parent
FRONT_HTML_PATH = BASE_DIR / "upbit_wallet_status_client.html"

app = Flask(__name__)


@app.after_request
def apply_cors_headers(response: Response) -> Response:
    """프론트에서 호출 가능하도록 CORS 헤더를 추가합니다."""
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return response


@app.route("/", methods=["GET"])
def index() -> Response:
    """간단한 테스트용 프론트 HTML을 제공합니다."""
    return send_file(FRONT_HTML_PATH)


@app.route("/api/upbit_wallet_status", methods=["GET", "OPTIONS"])
def upbit_wallet_status() -> Response:
    """업비트 입출금 상태를 서버에서 조회해 JSON으로 반환합니다."""
    if urllib.request is None:  # pragma: no cover
        return jsonify({"error": "internal error"}), 500

    req = urllib.request.Request(
        UPBIT_WALLET_STATUS_URL,
        headers={
            "Accept": "application/json",
            "User-Agent": "upbit-wallet-status-proxy/1.0",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            payload = response.read().decode("utf-8")
            data = json.loads(payload)
            return jsonify({"source": "upbit", "count": len(data) if isinstance(data, list) else None, "data": data})
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="ignore") if hasattr(err, "read") else ""
        return jsonify({"error": f"Upbit API HTTP error: {err.code}", "details": body}), 502
    except urllib.error.URLError as err:
        return jsonify({"error": f"Upbit API network error: {err.reason}"}), 502
    except json.JSONDecodeError:
        return jsonify({"error": "Upbit API returned invalid JSON"}), 502
    except Exception as err:  # noqa: BLE001
        return jsonify({"error": f"Unexpected server error: {err}"}), 500


if __name__ == "__main__":
    # 개발 실행: python3 app.py
    app.run(host="0.0.0.0", port=8000, debug=True)
