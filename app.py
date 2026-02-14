#!/usr/bin/env python3
"""업비트 입출금 상태 프록시(비활성화 버전).

요청에 따라 업비트 입출금 확인/공지 파싱을 모두 사용하지 않습니다.
"""

from __future__ import annotations

from flask import Flask, jsonify, make_response, request, send_file

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

    return with_cors(
        make_response(
            jsonify(
                {
                    "ok": True,
                    "source": "disabled",
                    "message": "업비트 입출금 확인 기능은 비활성화되었습니다.",
                    "data": [],
                }
            ),
            200,
        )
    )


@app.route("/debug/upbit_raw", methods=["GET", "OPTIONS"])
def debug_upbit_raw():
    if request.method == "OPTIONS":
        return with_cors(make_response("", 200))

    return with_cors(
        make_response(
            jsonify(
                {
                    "source": "disabled",
                    "message": "업비트 공지 파싱/상태 조회를 사용하지 않습니다.",
                    "sample": [],
                    "errors": [],
                }
            ),
            200,
        )
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
