# 멀티체인 지갑 포트폴리오 대시보드

Ethereum + Solana 주소를 그룹 단위로 관리하고, 자산 수량/USDT/KRW 가치를 합산해 보여주는 조회 전용 웹앱입니다.

## 주요 기능
- 체인 어댑터 구조
  - `validateAddress()`
  - `fetchBalances()`
  - `buildExplorerUrl()`
- 지원 체인 (최소)
  - Ethereum (Etherscan)
  - Solana (Solscan)
- 주소 행별 Explorer 버튼 (`target="_blank"`)
- 그룹 단위 집계
  - 그룹 내 지갑 총액 (USDT/KRW)
  - 동일 자산 합산
- TTL 캐시 (기본 120초)
- 0 가치 토큰 숨김 토글
- JSON 백업/복원
- 프라이빗키/시드 미요구 (주소 조회 전용)

## 실행 방법
### 1) 일반 실행
1. Node.js 18+ 설치
2. 의존성 설치
   - `npm install`
3. 개발 서버 시작
   - `npm run dev`
4. 브라우저에서 `http://localhost:5173`

### 2) 더블클릭 실행 (Windows)
- `run.bat` 더블클릭
  - `node_modules` 없으면 자동으로 `npm install`
  - 브라우저 자동 오픈 후 dev 서버 실행

## API 키 / 환경변수
- Etherscan API 키는 선택 사항입니다.
  - 키가 없어도 최소 동작 모드로 시도합니다.
- 사용 방법
  1. `.env.example` 복사 후 `.env` 생성
  2. `VITE_ETHERSCAN_API_KEY=...` 입력
- 앱 내 Settings에서도 키를 직접 입력/저장 가능합니다.

## 데이터 소스
- Ethereum: Etherscan API
- Solana: Solana Public RPC + Solscan Explorer 링크
- 가격: CoinGecko Simple Price API
- 환율: open.er-api.com (USD->KRW)

## 배포
- Vercel / Netlify 모두 가능
- 기본 빌드 명령: `npm run build`
- 출력 디렉토리: `dist`

## 프로젝트 구조
- `src/adapters` 체인 어댑터
- `src/services` 캐시/가격/포트폴리오 집계
- `src/components` UI 구성 요소
- `src/store.ts` 그룹/주소/설정 상태 저장

## 범위
- 포함: 조회/집계 대시보드
- 제외: 거래/자동매매/차익거래
