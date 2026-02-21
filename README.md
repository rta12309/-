# Solscan 지갑 토큰 보유량 조회기

지갑 주소를 입력한 뒤, 그 지갑이 보유한 토큰 목록에서 **토큰 티커(symbol)** 를 선택(또는 직접 입력)해서 특정 토큰 보유량을 확인하는 CLI 프로그램입니다.

## 실행 방법

```bash
python3 solscan_wallet_token_checker.py
```

## 동작 방식

1. Solana 지갑 주소 입력
2. Solscan 공개 API(`public-api.solscan.io`)에서 토큰 목록 조회
3. 번호 / 티커(symbol) / 토큰 주소 중 하나로 조회 대상 토큰 선택
4. 해당 토큰의 보유량(raw, decimal 반영값) 출력

## 참고

- API 응답 형식이 변경되거나 Solscan 측 제한이 있는 경우 조회가 실패할 수 있습니다.
- 같은 티커를 가진 토큰이 여러 개일 수 있으므로, 필요 시 토큰 주소로 정확히 지정하세요.
