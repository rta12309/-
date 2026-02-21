# ChainScan 조건 지갑 필터

요청하신 조건으로 지갑을 찾을 수 있게 **웹 버전(설치 없이 실행)** + Python CLI 버전을 제공합니다.

## 웹 버전 (설치/압축해제 없이 바로 실행)
1. `index.html` 파일을 브라우저에서 바로 열기.
2. 체인, 티커(또는 CA), 날짜/시간, 옵션 입력.
3. 각 조건 입력칸 **옆 토글(적용 체크박스)** 로 ON/OFF 조절.
4. `스캔 실행` 클릭.

## 주요 변경
- 토글 위치를 별도 섹션이 아닌 **해당 입력칸 옆**으로 이동.
- `토큰 CA 주소(선택)` 라벨로 변경.
- holder API가 비어도 **최근 Transfer 로그 기반 fallback 후보 탐색** 추가.
- 모든 행동 조건 OFF 시 tx 분석 없이 후보를 바로 결과로 사용.

## “모든 조건 OFF인데도 0건” 가능 원인
1. Explorer holder API 제한 + fallback까지 비어있는 토큰.
2. USD 필터 ON 상태에서 fallback 후보(usd_value=0)가 전부 제외됨.
3. decimals/raw 설정 불일치로 수량 계산 실패.

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
