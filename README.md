# 초보자용 카운터 GUI

버튼으로 숫자를 올리거나( +1 ) 0으로 초기화(리셋)하는 아주 간단한 Python GUI 프로그램입니다.

## 기능
- 큰 숫자 표시 (기본값 0)
- **카운트 +1** 버튼: 숫자 1 증가
- **리셋** 버튼: 숫자 0으로 초기화
- 오류가 나면 팝업(messagebox)으로 안내
- 단축키 지원
  - `Space` 또는 `Enter`: +1
  - `r`: 리셋

## 준비사항
- Python 3 설치
- 별도 패키지 설치 불필요 (표준 라이브러리 `tkinter` 사용)

## 실행 방법 (가장 쉬운 방법)

### Windows
1. 이 폴더에서 `RUN_WINDOWS.bat` 파일을 더블클릭
2. 프로그램 창이 열리면 버튼을 눌러 사용

또는 터미널/명령 프롬프트에서:
```bash
python app.py
```

### macOS
1. 터미널에서 아래 명령으로 실행 권한 1회 부여
```bash
chmod +x RUN_MAC.command
```
2. `RUN_MAC.command` 더블클릭 (환경에 따라 보안 확인 필요)

또는 터미널에서:
```bash
python3 app.py
```

### Linux
터미널에서:
```bash
chmod +x RUN_MAC_LINUX.sh
./RUN_MAC_LINUX.sh
```

## 파일 설명
- `app.py`: 메인 GUI 프로그램
- `requirements.txt`: 의존성 정보 (실질적으로 추가 설치 없음)
- `RUN_WINDOWS.bat`: Windows 더블클릭 실행용
- `RUN_MAC.command`: macOS 더블클릭 실행용
- `RUN_MAC_LINUX.sh`: macOS/Linux 쉘 실행용
