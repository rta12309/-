# 업비트/빗썸 가격 차이 알림 프로그램

업비트와 빗썸의 동일 코인 가격 차이가 **5% 이상**이면 웹 화면에서 경고/알림음을 띄우는 프로그램입니다.

## 초보자용 실행 방법 (더블클릭)

### Windows
1. `run_windows.bat` 파일을 더블클릭합니다.
2. 처음 실행 시 자동으로 필요한 패키지를 설치합니다.
3. 브라우저가 자동으로 열리며 `http://127.0.0.1:5000` 에서 동작합니다.

### macOS / Linux
1. `run_mac_linux.command` 파일 실행 권한이 없으면 터미널에서 1회 실행:
   ```bash
   chmod +x run_mac_linux.command
   ```
2. `run_mac_linux.command` 더블클릭(또는 터미널 실행)합니다.

## 직접 실행 방법
```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```
Windows는 `.venv\\Scripts\\python app.py` 사용.

## 설정 변경
`config.json` 파일에서 아래 값을 바꿀 수 있습니다.
- `symbol`: 감시 코인 심볼 (예: BTC, ETH)
- `threshold_percent`: 알림 기준 퍼센트 (기본 5.0)
- `check_interval_seconds`: 가격 조회 주기
- `host`, `port`: 웹 서버 주소

## 알림 방식
- 웹 페이지의 상태 박스가 빨간색으로 변경
- 브라우저 팝업(alert)
- 짧은 경고음(beep)

> 참고: 브라우저 설정에 따라 팝업/소리 허용이 필요할 수 있습니다.
