# TodoMate Floating Widget

> todomate.net을 Windows 데스크톱 플로팅 위젯으로 띄워줍니다.

## 다운로드

[**최신 릴리즈에서 TodoMateWidget.exe 다운로드**](../../releases/latest)

## 기능

- **항상 최상위(always-on-top)** — 다른 창 위에 항상 표시
- **프레임 없는 깔끔한 UI** — 상단 바를 드래그하여 자유롭게 위치 이동
- **로그인 세션 자동 유지** — 앱을 재시작해도 로그인 상태 유지
- **시스템 트레이 제어** — 보이기/숨기기/위치 초기화/종료
- **닫기 버튼 = 트레이로 숨기기** — 트레이에서 '종료'로만 완전 종료

## 사용법

1. `TodoMateWidget.exe`를 다운로드하여 실행
2. todomate.net에 로그인 (최초 1회만)
3. 시스템 트레이 아이콘으로 제어

## 시스템 트레이 메뉴

| 메뉴 | 설명 |
|------|------|
| **보이기/숨기기** | 위젯 토글 (아이콘 더블클릭으로도 가능) |
| **위치 초기화** | 화면 우측 하단으로 이동 |
| **브라우저에서 열기** | 기본 브라우저에서 todomate.net 열기 |
| **종료** | 앱 완전 종료 |

## 요구사항

- Windows 10 / 11
- Microsoft Edge WebView2 Runtime (대부분 이미 설치되어 있음)

## 직접 빌드

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
pip install pyinstaller

# 실행 (개발)
python main.py

# .exe 빌드
pyinstaller build.spec
```

## 배포

```bash
git tag v1.0.0
git push origin v1.0.0
# → GitHub Actions가 자동 빌드 → Release에 .exe 첨부
```

## 면책

이 프로젝트는 TodoMate 공식 앱이 아닙니다.
todomate.net 웹사이트를 WebView로 표시하는 비공식 래퍼입니다.

## 라이선스

[MIT](LICENSE)
