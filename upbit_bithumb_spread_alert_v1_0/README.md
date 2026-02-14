# Spread Alert v1.0 (Upbit↔Bithumb 가격차 알림기)

업비트/빗썸 동일 코인의 KRW 가격차를 주기적으로 비교하고, 설정 임계치(기본 5%) 이상일 때 알림을 보냅니다.

> 핵심 안전장치: **입금/출금 중 하나라도 불가이면 알림을 차단**합니다.

---

## 1) 그냥 실행 (배포 EXE 더블클릭)

1. `dist/SpreadAlert_v1.0.exe` 파일을 더블클릭합니다.
2. 같은 폴더의 `config/config.json`을 원하는 값으로 수정합니다.
3. 실행 후 `alerts.log`를 열어 동작 로그/알림 여부를 확인합니다.

---

## 2) 개발 실행 (run.bat 더블클릭)

1. `scripts/run.bat`를 더블클릭합니다.
2. 자동으로:
   - `.venv` 가상환경 생성(최초 1회)
   - 라이브러리 설치
   - 앱 실행
3. 종료하려면 콘솔에서 `Ctrl + C`.

---

## 3) 빌드 점검 (build_release.bat)

1. `scripts/build_release.bat` 더블클릭
2. Python 소스 컴파일 점검 수행
3. 오류 없으면 빌드 준비 완료

---

## 4) 배포 EXE 만들기 (publish_exe.bat)

1. `scripts/publish_exe.bat` 더블클릭
2. 자동으로 PyInstaller 단일 실행파일 생성
3. 산출물: `dist/SpreadAlert_v1.0.exe`

---

## 5) 설정(config.json) 바꾸는 법

파일 위치: `config/config.json`

주요 항목:
- `threshold_percent`: 알림 임계치(기본 5)
- `interval_seconds`: 조회 주기(기본 10초)
- `cooldown_seconds`: 동일 코인 재알림 쿨다운(기본 300초)
- `symbols_mode`: `ALL` 또는 `LIST`
- `symbols_list`: `LIST`일 때만 사용
- `use_absolute_diff`: true면 ±절대값 기준
- `notify_channels`: `desktop`, `telegram` 조합
- `telegram_token`, `telegram_chat_id`: 텔레그램 사용 시 필수
- `enable_network_match`: 네트워크 매칭 보수 모드

### 설정 변경 반영
- 현재 버전은 루프마다 `config.json`을 다시 읽으므로 재시작 없이 반영됩니다.

---

## 6) 텔레그램 알림 설정(선택)

1. BotFather로 봇 생성 후 토큰 발급
2. 본인/그룹 chat_id 확인
3. `config.json` 설정:
   - `notify_channels`에 `telegram` 추가
   - `telegram_token`, `telegram_chat_id` 입력
4. 앱 재실행 또는 다음 루프에서 적용

> 주의: 토큰은 로그에 마스킹되어 기록됩니다.

---

## 동작 상세

- 가격차 계산식(기본):
  - `(업비트 - 빗썸) / 빗썸 * 100`
- 알림 조건:
  1. 가격차가 임계치 이상
  2. 업비트/빗썸 **모두 입금 가능 + 출금 가능**
  3. 쿨다운 초과 또는 직전 알림 대비 격차가 +1%p 이상 확대
- 로그 파일: `alerts.log`
  - 타임스탬프, 코인, 양 거래소 가격, 차이%, 상태, 알림 여부 기록

---

## 입출금/네트워크 제한사항 (중요)

- 업비트: 공개 API에서 지갑 상태(코인/네트워크 정보)를 사용
- 빗썸: 공개 API는 주로 **코인 단위 입출금 상태**를 제공
- 따라서 `enable_network_match=true`라도 완전한 동일 네트워크 교집합 판정은 거래소 공개 데이터 한계가 있습니다.
- 본 버전은 보수적으로 동작하며, 상태 불명확 시 알림 차단 방향을 우선합니다.

---

## 검증 시나리오

1. 정상 케이스
   - 임계치를 낮춰(`threshold_percent=0.1`) 실행
   - 조건 충족 코인에서 알림 발생 확인
2. 차단 케이스
   - 입출금 불가 코인(거래소 상태 기준)에서 가격차가 커도 알림 미발생 확인
   - `alerts.log`의 `status=...`와 `alert=False` 확인
3. 장애 케이스
   - 일시 네트워크 단절 또는 API 실패 상황에서 프로세스가 종료되지 않고 다음 루프 지속 확인

---

## 오류 발생 시 복사해서 보내기 템플릿

아래 템플릿을 복사해서 전달하세요.

```text
[Spread Alert v1.0 오류 제보 템플릿]
- 실행한 파일명:
- 콘솔 출력 전체:
- alerts.log 일부(최근 50줄):
- config.json(민감정보 토큰은 마스킹):
- Windows 버전:
- python --version / pip freeze:
```

동일 템플릿은 `BUGFIX.md`에도 포함되어 있습니다.
