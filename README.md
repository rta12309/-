# ChainScan 조건 지갑 필터

특정 체인/날짜/토큰 티커를 입력받아, 체인 스캔 API 데이터를 기반으로 아래 조건에 맞는 지갑 리스트를 CSV로 저장합니다.

## 필터 조건
1. 특정 체인의 특정 토큰 홀더 중 보유 달러 가치가 `300k ~ 30m`.
2. 해당 지갑의 **해당 토큰 트랜잭션 첫 시점이 지정 날짜 이후**.
3. 지정 날짜 이후의 해당 토큰 트랜잭션에서, 대부분(기본 80%)이 **입금(inbound)** 이고,
   **여러 송신자 주소(기본 3개 이상)** 에서 들어오는 패턴.

## 지원 체인
- ethereum (Etherscan)
- bsc (BscScan)
- polygon (PolygonScan)
- arbitrum (Arbiscan)
- optimism (Optimistic Etherscan)

## 실행 방법
```bash
python3 wallet_scanner.py \
  --chain ethereum \
  --ticker USDT \
  --scan-api-key <YOUR_SCAN_API_KEY> \
  --since 2025-01-01T00:00:00 \
  --holder-quantity-is-raw \
  --decimals 6 \
  --output wallet_signals.csv
```

## 주요 옵션
- `--chain`: 체인 선택.
- `--ticker`: 토큰 티커 입력.
- `--since`: 기준 날짜/시간(UTC, `YYYY-MM-DD` 또는 `YYYY-MM-DDTHH:MM:SS`).
- `--token-address`: 컨트랙트 주소 직접 입력(입력 시 티커 탐색 생략).
- `--holder-quantity-is-raw`: 홀더 수량이 raw 값일 때 사용.
- `--decimals`: raw 수량의 decimals.
- `--min-usd`, `--max-usd`: 보유 달러 가치 필터 범위.
- `--inbound-ratio-threshold`: 입금 비율 임계치.
- `--min-unique-senders`: 최소 송신자 수.

## 참고
- 일부 Scan API의 `tokenholderlist`/`tokeninfo` 계열은 요금제 제한이 있을 수 있습니다.
- 티커 심볼이 중복되는 경우 CoinGecko 시가총액 기준으로 가장 큰 후보를 자동 선택합니다.
