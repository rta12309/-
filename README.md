# ChainScan 조건 지갑 필터

요청하신 조건으로 지갑을 찾을 수 있게 **웹 버전(설치 없이 실행)** + Python CLI 버전을 제공합니다.

이번 업데이트로 웹에서 각 탐색 조건을 ON/OFF 하며 결과가 0건인 원인을 단계적으로 확인할 수 있습니다.

## 웹 버전 (설치/압축해제 없이 바로 실행)
1. `index.html` 파일을 브라우저에서 바로 열기.
2. 체인, 티커(또는 CA), 날짜/시간, 옵션 입력.
3. 필요하면 각 조건(USD 범위, 첫 트랜잭션 시점, 입금 비율, 최소 송신자 수)을 ON/OFF 조절.
4. `스캔 실행` 클릭.
5. 결과를 표로 확인하고 `CSV 다운로드` 클릭.

> API Key는 **선택 입력**입니다. 비워도 실행되지만, 체인 API 제한이 더 빨리 걸릴 수 있습니다.

## 웹 입력값 안내 (초보자용)
- **티커**: 예) `USDT`
- **CA 주소**: 토큰 컨트랙트 주소(`0x...`). 티커 옆 칸에 있으며, 입력하면 자동 탐색을 건너뜁니다.
- **기준 날짜/시간**: `datetime-local` 형식, 기본값은 `2025-01-01T00:00`처럼 **분 단위**까지 들어갑니다.
- **홀드 수량 Decimals**:
  - 토큰 수량의 소수점 자릿수입니다.
  - 예) USDT는 보통 6, 대부분 ERC-20은 보통 18
- **raw 값이면 체크**:
  - Explorer에서 수량이 사람이 읽기 전 정수값으로 올 때 사용.
  - 예) 1 USDT(6 decimals) = `1000000` (raw)


## 탐색 조건 ON/OFF (웹)
- **USD 보유가치 범위 사용**: 300k~30m 범위를 적용/해제합니다.
- **첫 트랜잭션이 기준시각 이후**: 이 조건이 엄격해서 0건이 나올 수 있으니 필요시 OFF 하세요.
- **입금 비율 조건**: 기준 시각 이후 tx 중 입금 비율 조건 적용/해제.
- **최소 송신자 수 조건**: 여러 주소에서 입금되는 패턴 조건 적용/해제.

> 추천 디버깅 순서: 전부 OFF로 돌려서 후보가 나오는지 확인 -> 조건을 하나씩 ON 하며 어느 조건에서 0건이 되는지 확인.

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

## Python CLI 실행 방법 (선택)
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

## 주요 옵션 (CLI)
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
- 일부 Scan API의 `tokenholderlist` 계열은 요금제 제한이 있을 수 있습니다.
- 티커 심볼이 중복되는 경우 CoinGecko 시가총액 기준으로 가장 큰 후보를 자동 선택합니다.
