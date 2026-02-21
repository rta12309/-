# ChainScan 조건 지갑 필터

요청하신 조건으로 지갑을 찾을 수 있게 **웹 버전(설치 없이 실행)** + Python CLI 버전을 제공합니다.

## 웹 버전 (설치/압축해제 없이 바로 실행)
1. `index.html` 파일을 브라우저에서 바로 열기.
2. 체인, 티커(또는 CA), 날짜/시간, 옵션 입력.
3. 각 조건 입력칸 **옆 토글(적용 체크박스)** 로 ON/OFF 조절.
4. `스캔 실행` 클릭.

## Quantity 처리 방식 (요청 반영)
- 별도의 `raw 체크` / `decimals` 수동 입력을 제거했습니다.
- 홀더 Quantity 값에서 **소수점 5자리 이상이 보이면 decimal 수량으로 간주**해서 그대로 사용합니다.
- 소수점이 거의 없거나 정수 형태면 raw로 보고, 토큰 컨트랙트 `decimals()`를 자동 조회해서 보정합니다.

## 주요 변경
- 토글 위치를 해당 입력칸 옆으로 간소화.
- `토큰 CA 주소(선택)` 라벨 유지.
- holder API가 비어도 최근 Transfer 로그 기반 fallback 후보 탐색.
- 모든 행동 조건 OFF 시 tx 분석 없이 후보를 바로 결과로 사용.

## “모든 조건 OFF인데도 0건” 가능 원인
1. Explorer API(특히 holder/로그)가 무료 플랜 제한으로 빈 응답.
2. 해당 토큰의 최근 on-chain 활동(Transfer 로그) 자체가 적음.
3. USD 필터 ON 상태에서 fallback 후보(usd_value=0)가 제외됨.

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
