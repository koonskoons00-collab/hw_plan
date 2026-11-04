# 대학생 과제 일정 관리 프로그램 (공휴일 API 업데이트)

## 1. 프로그램 소개

Python의 Tkinter로 만든 대학생 과제 일정 관리 프로그램이다. 과목명, 과제명, 마감 날짜와 시간을 등록하여 달력과 목록에서 확인할 수 있다. 기존의 과제 추가, 수정, 삭제, 완료 처리, 남은 시간 확인, 3일 이내 마감 과제 알림 기능을 유지하면서 **대한민국 공휴일 API**를 연동했다.

## 2. API 적용 기능

Nager.Holidays의 무료 Community API v4를 활용한다. 프로그램 실행 시 현재 연도의 공휴일 정보를 조회하고, 달력의 공휴일 칸을 연분홍색으로 표시한다. 날짜를 클릭하면 공휴일 이름을 확인할 수 있다. 과제 마감 날짜가 공휴일인 경우 목록의 과제명 뒤에 `[공휴일]`이 나타난다. 상단의 `공휴일 새로고침` 버튼을 누르면 정보를 다시 가져온다. 연도가 바뀌면 새 연도를 조회한다.

- API 문서: https://nagerholidays.com/api
- 요청 주소: `https://nagerholidays.com/api/v4/Holidays/KR/{year}`
- API Key: **필요 없음**. 따라서 `.env` 파일을 설정하지 않아도 된다.
- 인터넷이 연결되지 않거나 API 호출이 실패해도 기존 과제 관리 기능은 계속 작동한다.

## 3. 실행 방법 (UV)

Python 3.10 이상과 UV가 필요하다. 프로젝트 최상위 폴더에서 실행한다.

```powershell
uv sync
uv run python main.py
```

인터넷 연결을 통해 공휴일 정보를 받아오며, 공휴일 표시가 없어도 과제 등록 및 조회는 가능하다. `uv.lock`을 포함했으므로 같은 의존성을 재현할 수 있다. GUI 실행에는 Windows/macOS 또는 Tkinter가 설치된 데스크톱 Linux가 필요하다.

## 4. 주요 코드 설명

| 파일 | 역할 |
|---|---|
| `main.py` | 화면 생성, 달력 및 과제 목록 갱신, API 결과를 달력에 반영 |
| `models.py` | 과제 정보와 JSON 저장·수정·완료 처리 |
| `dialogs.py` | 과제 추가·수정 및 완료 과제 관련 창 |
| `holiday_api.py` | URL 요청, JSON 파싱, 공휴일 날짜·이름 추출 |
| `assignments.json` | 등록한 과제 데이터 저장 |
| `api-plan.md` | API 적용 기획안 |

`fetch_public_holidays(year)`는 연도로 API를 호출한 다음 `holidayTypes`에 `Public`이 있고 `nationalHoliday`가 `true`인 날짜만 딕셔너리로 반환한다. `main.py`의 `_load_holidays()`는 작업 스레드에서 이를 호출하고, `_poll_holiday_queue()`는 Tkinter 메인 스레드에서 결과를 받는다. `refresh_all()`은 공휴일을 달력과 과제 목록에 적용한다. API 요청 실패 시 오류를 안내하고 프로그램을 종료하지 않는다.

## 5. 테스트 및 주의 사항

```powershell
uv run python -m unittest -v test_holiday_api.py
```

직접 확인할 항목: 과제 등록/수정/완료/삭제, 휴일 날짜 표시, 공휴일과 겹치는 과제 경고, 연도 이동 시 새 데이터 조회, 인터넷 연결 실패 시 정상 실행. 공휴일은 **과제 마감 자동 연장**을 뜻하지 않으므로 실제 마감일은 교수자 공지를 따르도록 한다.

## 6. GitHub 업데이트 방식

별도 `feature/holiday-api` 브랜치에서 작업한 뒤 Pull Request를 생성해 `main`으로 병합한다. `.venv`, `__pycache__`, `.env` 등은 Git에 추가하지 않는다. 사용한 AI 대화 원문은 기존 `conversation.md` 파일에 실제 대화 내용을 추가한다.
