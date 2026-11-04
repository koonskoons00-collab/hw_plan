"""Nager.Holidays v4에서 대한민국 공휴일을 가져오는 모듈."""
import json
from datetime import date
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class HolidayApiError(Exception):
    """공휴일 API 조회에 실패했을 때 발생하는 오류."""


def fetch_public_holidays(year, opener=None):
    """year에 해당하는 전국 공휴일을 {날짜: 이름} 형태로 반환한다.

    Args:
        year (int): 조회할 연도.
        opener (callable | None): 테스트용 요청 함수. 기본값은 urlopen.
    """
    if not isinstance(year, int) or not 2000 <= year <= 2100:
        raise ValueError("연도는 2000~2100 사이의 정수여야 합니다.")
    url = f"https://nagerholidays.com/api/v4/Holidays/KR/{year}"
    request = Request(url, headers={"User-Agent": "hw-plan-student-project/1.0", "Accept": "application/json"})
    do_open = opener or urlopen
    try:
        with do_open(request, timeout=8) as response:
            data = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        raise HolidayApiError(f"공휴일 정보를 불러오지 못했습니다: {error}") from error

    if not isinstance(data, list):
        raise HolidayApiError("공휴일 API 응답 형식이 올바르지 않습니다.")

    holidays = {}
    try:
        for item in data:
            # 전국 법정 공휴일만 달력에 표시한다.
            if "Public" not in item.get("holidayTypes", []):
                continue
            if not item.get("nationalHoliday", False):
                continue
            day = item["date"]
            if date.fromisoformat(day).year != year:
                continue
            holidays[day] = item.get("name", "공휴일")
    except (TypeError, KeyError, ValueError, AttributeError) as error:
        raise HolidayApiError("공휴일 API 응답을 해석할 수 없습니다.") from error
    return holidays
