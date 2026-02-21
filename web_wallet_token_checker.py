#!/usr/bin/env python3
"""웹 기반 Solana 지갑 토큰 보유량 조회기 (Solscan 우선)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "0.0.0.0"
PORT = 8765
USER_AGENT = "Mozilla/5.0 (wallet-token-web-checker/1.1)"


@dataclass
class AttemptResult:
    source: str
    ok: bool
    detail: str


class ProviderError(RuntimeError):
    pass


def normalize_amount(raw_amount: str | int | float, decimals: int | str) -> str:
    try:
        base = Decimal(str(raw_amount))
        scale = Decimal(10) ** int(decimals)
        return format(base / scale, "f")
    except (InvalidOperation, ValueError, ArithmeticError):
        return "0"


def http_get_json(url: str, headers: dict[str, str]) -> object:
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ProviderError(f"HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise ProviderError(f"연결 실패: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise ProviderError("JSON 파싱 실패") from exc


def parse_public_api_tokens(data: object) -> list[dict]:
    if not isinstance(data, list):
        raise ProviderError("응답 형식 불일치(list 아님)")

    parsed: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        amount_obj = item.get("tokenAmount") or {}
        raw_amount = amount_obj.get("amount", 0)
        decimals = amount_obj.get("decimals", 0)
        parsed.append(
            {
                "symbol": item.get("tokenSymbol") or "(티커 없음)",
                "token_address": item.get("tokenAddress") or "",
                "raw_amount": str(raw_amount),
                "decimals": int(decimals) if str(decimals).isdigit() else 0,
                "ui_amount": normalize_amount(raw_amount, decimals),
                "source": "solscan-public-api",
            }
        )
    return parsed


def parse_v2_token_accounts(data: object) -> list[dict]:
    if not isinstance(data, dict):
        raise ProviderError("응답 형식 불일치(object 아님)")
    items = data.get("data")
    if not isinstance(items, list):
        raise ProviderError("응답에 data 배열이 없음")

    parsed: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        raw_amount = item.get("amount", 0)
        decimals = item.get("token_decimals", 0)
        parsed.append(
            {
                "symbol": item.get("token_symbol") or "(티커 없음)",
                "token_address": item.get("token_address") or "",
                "raw_amount": str(raw_amount),
                "decimals": int(decimals) if str(decimals).isdigit() else 0,
                "ui_amount": normalize_amount(raw_amount, decimals),
                "source": "solscan-v2",
            }
        )
    return parsed


def fetch_wallet_tokens(wallet_address: str) -> tuple[list[dict], list[AttemptResult]]:
    headers = {
        "accept": "application/json, text/plain, */*",
        "user-agent": USER_AGENT,
        "origin": "https://solscan.io",
        "referer": "https://solscan.io/",
    }

    attempts: list[AttemptResult] = []

    providers = [
        (
            "solscan-public-api",
            f"https://public-api.solscan.io/account/tokens?{urllib.parse.urlencode({'account': wallet_address})}",
            parse_public_api_tokens,
        ),
        (
            "solscan-v2-token-accounts",
            "https://api-v2.solscan.io/v2/account/token-accounts?"
            + urllib.parse.urlencode(
                {
                    "address": wallet_address,
                    "page": 1,
                    "page_size": 100,
                    "type": "token",
                }
            ),
            parse_v2_token_accounts,
        ),
    ]

    for source, url, parser in providers:
        try:
            data = http_get_json(url, headers=headers)
            tokens = parser(data)
            attempts.append(AttemptResult(source, True, f"성공 ({len(tokens)}개 토큰)"))
            return tokens, attempts
        except ProviderError as exc:
            attempts.append(AttemptResult(source, False, str(exc)))

    return [], attempts


HTML = """<!doctype html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Solscan 지갑 토큰 조회기</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 2rem; background:#f7f7fb; }
    .card { background: white; border-radius: 12px; padding: 1.2rem; max-width: 860px; box-shadow:0 2px 8px rgba(0,0,0,.08); }
    input, button, select { padding: .55rem; font-size: .95rem; }
    input, select { min-width: 280px; }
    button { cursor:pointer; }
    .row { margin:.8rem 0; display:flex; gap:.7rem; flex-wrap:wrap; align-items:center; }
    .muted { color:#666; font-size:.9rem; }
    table { border-collapse: collapse; width:100%; margin-top:.8rem; }
    th, td { border:1px solid #ddd; padding:.5rem; text-align:left; font-size:.92rem; }
    th { background:#fafafa; }
    .error { color:#b00020; white-space: pre-wrap; }
    .ok { color:#0b7a0b; }
  </style>
</head>
<body>
  <div class="card">
    <h2>Solscan 지갑 토큰 보유량 조회기</h2>
    <p class="muted">지갑 주소 입력 → 보유 토큰 목록 확인 → 토큰 티커 선택 또는 직접 입력</p>

    <div class="row">
      <label for="wallet">지갑 주소:</label>
      <input id="wallet" placeholder="예: So11111111111111111111111111111111111111112" />
      <button id="load">토큰 불러오기</button>
    </div>

    <div class="row">
      <label for="tokenSelect">토큰 선택:</label>
      <select id="tokenSelect"><option value="">(선택하세요)</option></select>
      <span>또는 티커 직접입력:</span>
      <input id="tokenInput" placeholder="예: USDC" style="min-width:140px" />
      <button id="check">보유량 확인</button>
    </div>

    <div id="status" class="muted"></div>
    <div id="error" class="error"></div>
    <div id="result"></div>
    <div id="table"></div>
  </div>

<script>
let tokens = [];

function escapeHtml(text){
  return String(text).replace(/[&<>"']/g, function(m){
    return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[m];
  });
}

function renderTokens(){
  const select = document.getElementById('tokenSelect');
  select.innerHTML = '<option value="">(선택하세요)</option>';
  tokens.forEach((t,i)=>{
    const opt = document.createElement('option');
    opt.value = String(i);
    opt.textContent = `${t.symbol} | ${t.ui_amount} | ${t.token_address || '(주소 없음)'}`;
    select.appendChild(opt);
  });

  const rows = tokens.map((t, i) =>
    `<tr><td>${i+1}</td><td>${escapeHtml(t.symbol)}</td><td>${escapeHtml(t.ui_amount)}</td><td>${escapeHtml(t.raw_amount)}</td><td>${escapeHtml(t.token_address || '')}</td></tr>`
  ).join('');
  document.getElementById('table').innerHTML = rows
    ? `<table><thead><tr><th>#</th><th>티커</th><th>보유량</th><th>Raw</th><th>토큰 주소</th></tr></thead><tbody>${rows}</tbody></table>`
    : '';
}

function findToken(){
  const selected = document.getElementById('tokenSelect').value;
  if (selected !== '') return tokens[Number(selected)];

  const input = document.getElementById('tokenInput').value.trim().toLowerCase();
  if (!input) return null;
  const matches = tokens.filter(t => (t.symbol || '').toLowerCase() === input || (t.token_address || '').toLowerCase() === input);
  if (matches.length === 1) return matches[0];
  if (matches.length > 1) throw new Error('같은 티커를 가진 토큰이 여러 개입니다. 목록에서 직접 선택하거나 토큰 주소를 입력하세요.');
  return null;
}

document.getElementById('load').onclick = async () => {
  document.getElementById('error').textContent = '';
  document.getElementById('result').innerHTML = '';
  const wallet = document.getElementById('wallet').value.trim();
  if (!wallet) {
    document.getElementById('error').textContent = '지갑 주소를 입력하세요.';
    return;
  }

  document.getElementById('status').textContent = '조회 중...';
  try {
    const res = await fetch('/api/wallet-tokens', {
      method:'POST', headers:{'content-type':'application/json'},
      body: JSON.stringify({wallet})
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || '조회 실패');
    }
    tokens = data.tokens || [];
    renderTokens();
    document.getElementById('status').textContent = `조회 완료: ${tokens.length}개 토큰`;
    if (data.attempts) {
      const details = data.attempts.map(a => `${a.source}: ${a.ok ? '✅' : '❌'} ${a.detail}`).join('\n');
      document.getElementById('status').textContent += `\n시도 로그:\n${details}`;
    }
  } catch (e) {
    document.getElementById('status').textContent = '';
    document.getElementById('error').textContent = String(e.message || e);
  }
};

document.getElementById('check').onclick = () => {
  document.getElementById('error').textContent = '';
  try {
    const token = findToken();
    if (!token) {
      document.getElementById('error').textContent = '토큰을 찾을 수 없습니다. 선택 목록 또는 티커/주소 입력을 확인하세요.';
      return;
    }
    document.getElementById('result').innerHTML = `
      <h3>조회 결과</h3>
      <p><b>티커:</b> ${escapeHtml(token.symbol)}</p>
      <p><b>토큰 주소:</b> ${escapeHtml(token.token_address || '(주소 없음)')}</p>
      <p><b>보유 수량:</b> ${escapeHtml(token.ui_amount)}</p>
      <p><b>Raw 수량:</b> ${escapeHtml(token.raw_amount)}</p>
      <p class="muted">source: ${escapeHtml(token.source || '')}</p>
    `;
  } catch (e) {
    document.getElementById('error').textContent = String(e.message || e);
  }
};
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        body = HTML.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/wallet-tokens":
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        try:
            length = int(self.headers.get("content-length", "0"))
            raw = self.rfile.read(length)
            payload = json.loads(raw.decode("utf-8"))
            wallet = str(payload.get("wallet", "")).strip()
        except Exception:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "잘못된 요청 형식입니다."})
            return

        if not wallet:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "지갑 주소를 입력하세요."})
            return

        tokens, attempts = fetch_wallet_tokens(wallet)
        attempts_payload = [attempt.__dict__ for attempt in attempts]

        if not tokens:
            self._send_json(
                HTTPStatus.BAD_GATEWAY,
                {
                    "error": "Solscan 조회에 실패했습니다. 아래 시도 로그를 확인하세요.",
                    "attempts": attempts_payload,
                },
            )
            return

        self._send_json(HTTPStatus.OK, {"tokens": tokens, "attempts": attempts_payload})


def run_server(port: int = PORT) -> None:
    print(f"웹 서버 실행: http://{HOST}:{port}")
    server = ThreadingHTTPServer((HOST, port), Handler)
    server.serve_forever()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="웹 기반 Solscan 지갑 토큰 보유량 조회기")
    parser.add_argument("--port", type=int, default=PORT, help="웹 서버 포트 (기본값: 8765)")
    args = parser.parse_args()

    run_server(args.port)
