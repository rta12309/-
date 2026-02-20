# 멀티 지갑 자산 대시보드

별도 다운로드/압축해제 과정 없이, 파일만 열면 바로 실행 가능한 정적 웹 앱입니다.

## 기능

- 그룹 여러 개 생성/삭제
- 그룹마다 지갑 주소 입력칸 추가/삭제 (최대 10개)
- 업비트 API(`KRW-USDT`) 기반 USDT/KRW 환율 조회
- Ethereum/Solana는 API 기반 토큰 조회 + USD/KRW 합계 계산
- BSC, Polygon, Arbitrum, Optimism, Avalanche, Base, TRON, Bitcoin 등 주요 체인은
  스캔 URL/API URL 바로가기 제공

## 실행

아래 중 편한 방법으로 바로 실행할 수 있습니다.

### 1) 파일 직접 열기

`index.html`을 브라우저에서 바로 열어도 UI는 동작합니다.
(단, 일부 브라우저 정책으로 외부 API 호출은 제한될 수 있습니다.)

### 2) 간단한 로컬 웹 서버 실행 (권장)

```bash
python3 -m http.server 4173
```

브라우저에서 `http://localhost:4173` 접속
