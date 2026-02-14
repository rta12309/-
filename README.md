# Upbit/Bithumb Price Gap Alert Web App

브라우저에서 사용하는 업비트/빗썸 API 호출이 CORS 정책에 막히면 `Failed to fetch` 오류가 발생할 수 있습니다.
이 저장소는 그 문제를 해결하기 위해 **프록시 내장 서버(`server.py`)**를 포함합니다.

## 기능

- 업비트 KRW 마켓과 빗썸 KRW 마켓 공통 코인 가격 실시간 비교
- 코인별 가격 차이율(%) 표시 및 임계치(기본 5%) 초과 감지
- 업비트/빗썸 입출금 가능 여부 표시
- **양 거래소 모두 입금+출금 가능할 때만** 텔레그램 알림 전송
- 코인별 알림 쿨다운(중복 알림 방지)

## 실행 방법 (Failed to fetch 해결)

### 권장 실행

```bash
python3 server.py
```

실행 후 브라우저에서 아래 주소로 접속하세요.

- `http://127.0.0.1:8000`

> `index.html`을 파일로 직접 여는 방식(`file://...`)은 브라우저 보안 정책 때문에 API 호출이 막힐 수 있습니다.

## 텔레그램 설정

1. BotFather로 봇 생성 후 Bot Token 발급
2. 본인 또는 그룹 Chat ID 확인
3. 앱에 Bot Token / Chat ID 입력 후 `텔레그램 테스트`

## 프록시 API 엔드포인트

- `GET /api/upbit/markets`
- `GET /api/upbit/ticker?markets=KRW-BTC,...`
- `GET /api/upbit/wallet-status`
- `GET /api/bithumb/ticker-all-krw`
- `GET /api/bithumb/assetsstatus-all`
- `POST /api/telegram/send`

## 참고

- 텔레그램 토큰/채팅 ID는 브라우저 `localStorage`에 저장됩니다.
- 운영 환경에서는 인증/접근제어를 추가해 서버를 보호하세요.
