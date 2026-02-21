# Solscan 지갑 토큰 보유량 조회기 (Web)

요청하신 대로 **웹 페이지 형태**로 사용할 수 있게 만들었습니다.

- 지갑 주소를 입력하고
- 해당 지갑의 토큰 목록을 불러온 뒤
- 토큰을 **드롭다운에서 선택**하거나 **티커/토큰주소를 직접 입력**해서
- 보유량을 확인할 수 있습니다.

## 실행 방법

```bash
python3 web_wallet_token_checker.py
# 또는 포트 변경
# python3 web_wallet_token_checker.py --port 9000
```

실행 후 브라우저에서 아래 주소를 여세요.

- `http://localhost:8765`

## 기능

- Solscan API를 우선으로 조회 시도
  - `public-api.solscan.io/account/tokens`
  - `api-v2.solscan.io/v2/account/token-accounts`
- 각 시도 결과(성공/실패 및 원인)를 화면에 로그로 표시
- 토큰 목록 표 출력 + 선택/직접입력 조회

## 403 오류 관련

현재 일부 환경(프록시/방화벽/네트워크 정책)에서는 Solscan 도메인 접속 자체가 `403`으로 차단될 수 있습니다.
이 경우 앱 내부에서 여러 Solscan 엔드포인트를 순차 시도하고, 실패 원인을 그대로 보여줍니다.

로컬 PC에서 사용 시에는 아래를 확인하면 해결 가능성이 큽니다.

1. 회사/기관 프록시에서 Solscan 도메인 허용
2. VPN/보안 SW가 HTTPS 터널을 차단하지 않는지 확인
3. 필요한 경우 Solscan Pro API 키를 사용하는 경로로 확장
