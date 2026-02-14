# BUGFIX 가이드 — Spread Alert v1.0

## 1) 먼저 확인할 것
- 인터넷 연결 상태
- `config/config.json` 문법(JSON 콤마/따옴표)
- 가상환경/의존성 설치 여부 (`scripts/run.bat` 재실행)

## 2) 자주 발생하는 문제
- `requests` 관련 오류: 패키지 미설치 → `run.bat` 다시 실행
- 텔레그램 실패: 토큰/chat_id 오입력 또는 봇 권한 부족
- 데스크톱 알림 미표시: Windows 알림 설정 OFF, 또는 fallback 콘솔 출력 확인

## 3) 로그 확인
- `alerts.log`에서 `loop failed but continuing` 메시지를 우선 확인
- 거래소 API 일시 실패는 자동 재시도 후 다음 루프로 진행 (프로세스 종료 안 함)

## 4) 복사해서 보내기 템플릿

```text
[Spread Alert v1.0 오류 제보 템플릿]
- 실행한 파일명:
- 콘솔 출력 전체:
- alerts.log 일부(최근 50줄):
- config.json(민감정보 토큰은 마스킹):
- Windows 버전:
- python --version / pip freeze:
```
