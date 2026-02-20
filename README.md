# 멀티체인 지갑 포트폴리오 대시보드

**ERR_CONNECTION_REFUSED 대응 완료:** 기본 실행 경로를 `npm install` 없이 동작하는 **정적 웹앱 + 로컬 서버 방식**으로 변경했습니다.

## 핵심 기능
- 멀티체인 주소 조회 (Ethereum, Solana)
- 주소별 Explorer 링크 동적 생성
  - Ethereum: `https://etherscan.io/address/{address}`
  - Solana: `https://solscan.io/account/{address}`
- 그룹 단위 지갑 관리
  - 그룹 생성/삭제/이름변경
  - 주소 추가/삭제/별칭
- 집계
  - 자산 종류/수량
  - 자산별 USDT, KRW 가치
  - 주소 총액, 그룹 총액
- 설정
  - TTL 캐시 (기본 120초)
  - 0가치 토큰 숨김
  - Etherscan API Key(선택)
- JSON 백업/복원
- 프라이빗키/시드 입력 없음 (조회 전용)

## 빠른 실행 (무설치 중심)
### Windows (더블클릭)
1. `run.bat` 실행
2. 브라우저에서 `http://localhost:8787` 자동 오픈

`run.bat`는 다음 순서로 서버를 시도합니다.
1) `python -m http.server`
2) `py -m http.server`
3) `npx serve`

### 수동 실행 (모든 OS)
- Python 사용 시:
  - `python -m http.server 8787`
- 접속:
  - `http://localhost:8787`

## API/데이터 소스
- Ethereum 잔액/토큰: Etherscan API
- Solana 잔액/토큰: Solana RPC
- 가격(USDT): CoinGecko
- 환율(USD→KRW): open.er-api

## 참고
- 일부 공개 API의 Rate Limit/CORS/네트워크 상태에 따라 특정 주소만 부분 실패가 표시될 수 있습니다.
- 부분 실패 시에도 Explorer 링크와 나머지 데이터는 계속 표시됩니다.

## 선택 실행 (기존 Vite 소스)
기존 `src/` 기반 Vite 개발 구조도 저장소에 남아 있습니다. 네트워크가 허용되는 환경에서는 아래로 실행 가능합니다.
- `npm install`
- `npm run dev`
