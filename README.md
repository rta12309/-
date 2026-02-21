# ChainScan 조건 지갑 필터

요청하신 조건으로 지갑을 찾을 수 있게 **웹 버전(설치 없이 실행)** + Python CLI 버전을 제공합니다.

## 웹 버전 (설치/압축해제 없이 바로 실행)
1. `index.html` 파일을 브라우저에서 바로 열기.
2. 체인, 티커(또는 CA), 날짜/시간, 옵션 입력.
3. 각 조건 입력칸 **옆 토글(적용 체크박스)** 로 ON/OFF 조절.
4. 전체 탐색은 `스캔 실행`, 특정 주소 검증은 `특정 지갑 조건 체크` 버튼 클릭.

## 신규 기능: 특정 지갑 조건 체크
- `특정 지갑 주소 체크(선택)` 칸에 주소를 입력하고 버튼을 누르면,
  - 해당 지갑의 토큰 잔고(USD),
  - 행동 조건(첫 tx 시점/입금비율/송신자수)
  를 개별로 평가해서 통과 여부를 로그로 보여줍니다.
- 전체 탐색이 0건일 때, 특정 주소가 왜 탈락하는지 원인 파악에 유용합니다.


## Ethereum 보유량 조회 방식 (요청 반영)
- Ethereum 체인에서 특정 지갑 체크 시, 먼저 **Ethplorer + EVM 네이티브(Cloudflare RPC) 병합 방식**으로 토큰/잔고 USD를 조회합니다.
- 병합 조회 실패 또는 대상 토큰 미포함 시에만 `tokenbalance` 방식으로 재시도합니다.
- 그래서 이전처럼 `balance=NaN, usd=NaN`으로 바로 탈락하는 케이스를 줄였습니다.

## Quantity 처리 방식
- 별도의 `raw 체크` / `decimals` 수동 입력을 제거했습니다.
- 홀더 Quantity 값에서 **소수점 5자리 이상이 보이면 decimal 수량으로 간주**해서 그대로 사용합니다.
- 소수점이 거의 없거나 정수 형태면 raw로 보고, 토큰 컨트랙트 `decimals()`를 자동 조회해서 보정합니다.

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
