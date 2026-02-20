# 멀티 지갑 자산 대시보드

초보자도 쉽게 쓸 수 있게 만든 **설치 없는 정적 웹 앱**입니다.

## 꼭 먼저 알아두세요

- `index.html` 파일을 **더블클릭으로 바로 열면** 화면은 보이지만,
  브라우저 보안(CORS) 때문에 환율/자산 API 조회가 막힐 수 있습니다.
- 그래서 아래처럼 **로컬 서버 실행 방식**을 권장합니다.

## 가장 쉬운 실행 방법 (권장)

프로젝트 폴더 안에 있는 실행 파일 중 하나를 더블클릭하세요.

- Windows: `run_local_server.bat`
- macOS: `run_local_server.command`
- Linux: `run_local_server.sh`

실행 후 브라우저에서 `http://localhost:4173` 열면 됩니다.

## 수동 실행 방법

```bash
python3 -m http.server 4173
```

브라우저에서 `http://localhost:4173` 접속

## 기능

- 그룹 여러 개 생성/삭제
- 그룹마다 지갑 주소 입력칸 추가/삭제 (최대 10개)
- 업비트 API(`KRW-USDT`) 기반 USDT/KRW 환율 조회
- Ethereum/Solana: API 기반 토큰 조회 + USD/KRW 합계 계산
- BSC, Polygon, Arbitrum, Optimism, Avalanche, Base, TRON, Bitcoin:
  스캔 URL/API URL 바로가기 제공

## 자주 묻는 문제

### 1) API URL 누르면 `Invalid address format`가 떠요

유효하지 않은 주소이거나, 주소를 입력하지 않은 상태에서 API를 열어서 발생하는 오류입니다.
이번 버전부터는 주소 형식이 맞을 때만 API URL이 활성화됩니다.

### 2) 지갑 주소를 넣어도 자산 조회가 안 돼요

- `file://`로 열었을 가능성이 큽니다. `run_local_server`로 실행해 주세요.
- 체인과 주소 형식이 맞지 않으면 조회가 실패합니다.
  (예: Solana 주소를 Ethereum으로 조회)
