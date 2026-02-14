# Upbit/Bithumb Price Gap Alert Web App

브라우저에서 바로 실행 가능한(빌드/설치 불필요) 업비트-빗썸 가격차이 알림 웹앱입니다.

## 기능

- 업비트 KRW 마켓과 빗썸 KRW 마켓 공통 코인 가격을 실시간 비교
- 코인별 가격 차이율(%) 표시 및 임계치 초과 감지 (기본 5%)
- 업비트/빗썸 입출금 가능 여부 표시
- **양 거래소 모두 입금+출금 가능할 때만** 알림 전송
- 텔레그램 봇으로 차이율 알림 전송
- 코인별 알림 쿨다운(중복 알림 방지)

## 실행 방법

### 1) 파일 다운로드 후 브라우저에서 열기

`index.html` 파일을 브라우저에서 열면 바로 동작합니다.

### 2) 로컬 서버(권장)

브라우저 보안 정책으로 인해 일부 환경에서 CORS 문제가 생길 수 있으니, 아래처럼 간단 서버 실행을 권장합니다.

```bash
python3 -m http.server 8000
```

그 후 `http://localhost:8000` 접속.

## 텔레그램 설정

1. BotFather로 봇 생성 후 Bot Token 발급
2. 본인 또는 그룹 Chat ID 확인
3. 앱에 Bot Token / Chat ID 입력 후 `텔레그램 테스트`

## 데이터 소스

- Upbit Market: `https://api.upbit.com/v1/market/all`
- Upbit Ticker: `https://api.upbit.com/v1/ticker`
- Upbit Wallet Status: `https://api.upbit.com/v1/status/wallet`
- Bithumb Ticker: `https://api.bithumb.com/public/ticker/ALL_KRW`
- Bithumb Asset Status: `https://api.bithumb.com/public/assetsstatus/ALL`

## 참고

- 텔레그램 토큰/채팅 ID는 브라우저 `localStorage`에 저장됩니다.
- 민감한 운영 환경에서는 서버 백엔드를 두고 토큰을 서버에서 안전하게 관리하세요.
