# 업비트-빗썸 가격 차이 알림 앱

모든 코인(업비트 KRW 마켓 기준) 중 **업비트와 빗썸 양쪽에 공통 상장된 코인**을 대상으로,
가격 차이가 지정한 퍼센트(기본 5%) 이상이면 알림을 출력합니다.

## 코딩 몰라도 실행하는 방법 (윈도우 버튼 방식)

1. 이 폴더를 통째로 다운로드 받습니다.
2. 폴더 안의 `run_price_gap_alert_gui.bat` 파일을 **더블클릭**합니다.
3. 창이 뜨면:
   - `알림 기준(%)` 입력 (예: `5`)
   - `조회 간격(초)` 입력 (예: `10`)
   - **[시작]** 버튼 클릭
4. 1번만 확인하고 싶으면 **[한번만 조회]** 버튼 클릭

> 만약 창이 안 뜨고 Python 관련 오류가 나오면 Python 3를 설치한 뒤 다시 실행하세요.

## GUI 앱 파일

- `price_gap_alert_gui.py`: 버튼형 UI 앱
- `run_price_gap_alert_gui.bat`: 윈도우 더블클릭 실행 파일

## CLI(명령어) 방식도 가능

```bash
python3 price_gap_alert.py
```

## CLI 옵션

- `--threshold`: 알림 기준 퍼센트 (기본값 `5`)
- `--interval`: 조회 간격 초 (기본값 `10`)
- `--once`: 1회만 조회 후 종료

예시:

```bash
python3 price_gap_alert.py --threshold 5 --interval 15
python3 price_gap_alert.py --threshold 7.5 --once
```

## 동작 방식

1. 업비트 KRW 마켓 목록 조회
2. 업비트 실시간 거래가 조회
3. 빗썸 KRW 전체 티커 조회
4. 공통 심볼에 대해 `abs(업비트-빗썸)/빗썸*100` 계산
5. 임계치 이상이면 정렬해서 출력

## 참고

- 입금/출금이 한 곳이라도 불가능한 코인은 `입출금 제한 코인`으로 따로 표시하고, 가격차이 알림 대상에서 제외합니다.
- 입출금 상태 API(특히 업비트)에서 401 등 오류가 발생하면 경고만 출력하고, 가격 차이 조회는 중단하지 않습니다.
- GUI에서는 알림 시 PC 벨 소리를 시도합니다(환경에 따라 무음일 수 있음).
- 업비트 티커는 API 제한(최대 100개 마켓/요청)을 고려해 배치 조회합니다.
- `--once` 모드에서 네트워크/처리 오류가 발생하면 종료 코드 1로 반환합니다.

## 설치 없이 웹에서 자동 탐색 + 텔레그램 알림 (실험 기능)

- `web_price_gap_alert.html` 파일을 브라우저에서 열면 설치 없이 실행됩니다.
- `간격(초)`를 넣고 **자동 시작**을 누르면 n초마다 자동 탐색합니다.
- `텔레그램 봇 토큰`, `텔레그램 챗 ID`를 입력하면 조건 충족 시 텔레그램으로 알림을 전송합니다.
- **텔레그램 테스트** 버튼으로 토큰/챗ID가 정상인지 먼저 확인할 수 있습니다.
- 결과 테이블에 각 코인의 `업비트 입/출금`, `빗썸 입/출금` 상태와 **상태 출처(공식API)**를 함께 표시합니다.
- 업비트 입출금 상태 조회는 `api.upbit.com` 실패 시 `sg/id/th/global-api.upbit.com` 엔드포인트까지 순차 재시도합니다.
- 더따리 크롤링 fallback은 제거했습니다. 입출금 상태는 업비트/빗썸 공식 API로만 조회합니다.
- 업비트 입출금 조회는 `api/sg/id/th/global-api.upbit.com` 엔드포인트를 순차 재시도하고, 응답 필드 형식 차이도 함께 처리합니다.
- 업비트/빗썸 입출금 상태 API가 401/차단될 경우, 해당 경고를 표시하고 **가격 차이 계산은 계속 진행**합니다.
- 조회 중에는 로딩 아이콘(회전 스피너)로 앱이 멈춘 것이 아닌지 바로 확인할 수 있습니다.
- GitHub Pages에 이 파일을 올리면 웹 링크로 바로 실행할 수 있습니다.

## CORS 해결용 업비트 프록시 서버 (Flask)

브라우저에서 업비트 `https://api.upbit.com/v1/status/wallet`를 직접 호출하면 CORS/인증 문제로 실패할 수 있습니다.
이 프로젝트는 아래 구조로 해결합니다.

- 프론트 → `GET/POST /api/*` (내 서버만 호출)
- 내 서버 → 업비트 API 호출(JWT 인증)
- 내 서버가 JSON 결과만 프론트에 전달

### 파일

- `app.py`: Flask 프록시 서버 (CORS, preflight, 키 저장/로드, JWT 인증 호출)
- `upbit_wallet_status_client.html`: 초보자용 버튼 UI(키 저장/테스트/입출금 조회)
- `RUN_WINDOWS.bat`: 윈도우 더블클릭 실행 파일

### 의존성 설치

```bash
python3 -m pip install flask requests pyjwt
```

### 실행

- 일반 실행:

```bash
python3 app.py
```

- 윈도우 더블클릭 실행:
  - `RUN_WINDOWS.bat`

브라우저 접속:

- `http://127.0.0.1:8000/`

### API 키 저장 방식

- `POST /api/upbit_keys`
  - 입력 JSON: `{ "access_key": "...", "secret_key": "..." }`
  - 프로젝트 폴더의 `config.json`에 저장
- `GET /api/upbit_keys`
  - 저장 여부만 반환
  - 예: `{ "has_access_key": true, "has_secret_key": true }`

보안을 위해 `config.json`은 Git에 올리면 안 됩니다.
(이 저장소는 `.gitignore`에 `config.json`을 포함합니다.)

### 인증(JWT) 호출

- `GET /api/upbit_key_test`
  - 저장된 키로 인증 테스트(업비트 계정 조회 API 호출)
- `GET /api/upbit_wallet_status`
  - 저장된 키로 `/v1/status/wallet` 호출
- 키가 없으면 아래 JSON 반환:

```json
{"error":"MISSING_UPBIT_KEYS","hint":"Add UPBIT_ACCESS_KEY/UPBIT_SECRET_KEY"}
```

### 디버그/헬스

- `GET /health` → `{"ok": true}`
- `GET /debug/upbit_raw` → 업비트 상태코드 + 본문 미리보기

### CORS / preflight

- 모든 응답(성공/오류/예외)에 CORS 헤더를 붙입니다.
- `OPTIONS` 요청을 명시 처리합니다.
  - `Access-Control-Allow-Origin: *`
  - `Access-Control-Allow-Methods: GET, POST, OPTIONS`
  - `Access-Control-Allow-Headers: Content-Type, Authorization`
