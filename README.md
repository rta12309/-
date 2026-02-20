# 멀티 지갑 자산 대시보드

초보자도 쉽게 쓸 수 있게 만든 **설치 없는 정적 웹 앱**입니다.

## 가장 쉬운 실행 방법 (권장)

프로젝트 폴더 안 실행 파일을 더블클릭하세요.

- Windows: `run_local_server.bat`
- macOS: `run_local_server.command`
- Linux: `run_local_server.sh`

브라우저에서 `http://localhost:4173` 열면 됩니다.

## 수동 실행 방법

```bash
python3 -m http.server 4173
```

## 주요 기능

- 그룹 여러 개 생성/삭제
- 그룹마다 지갑 주소 입력칸 추가/삭제 (최대 10개)
- 전체조회 누르면 환율도 같이 자동 새로고침
- 자동 전체조회 ON/OFF + N초 주기 설정
- 업비트 API(`KRW-USDT`) 기반 환율 조회
- KRW는 `억` 단위(소수점 둘째 자리)로 표시
- Ethereum/Solana + BSC/Polygon/Arbitrum/Optimism/Avalanche/Base/TRON/Bitcoin 조회 지원

## 사용 팁

- 체인에 맞는 주소를 입력해야 조회됩니다.
- `API URL`, `스캔 URL`은 유효한 주소 입력 시에만 활성화됩니다.
