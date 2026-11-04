import io
import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from holiday_api import HolidayApiError, fetch_public_holidays


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


class HolidayApiTests(unittest.TestCase):
    def test_public_national_holidays_only(self):
        sample = [
            {"date": "2026-01-01", "name": "New Year's Day", "nationalHoliday": True, "holidayTypes": ["Public"]},
            {"date": "2026-01-10", "name": "Regional Holiday", "nationalHoliday": False, "holidayTypes": ["Public"]},
            {"date": "2026-01-11", "name": "Observance", "nationalHoliday": True, "holidayTypes": ["Observance"]},
        ]
        def fake_open(request, timeout):
            self.assertIn("/Holidays/KR/2026", request.full_url)
            return FakeResponse(json.dumps(sample).encode())
        result = fetch_public_holidays(2026, opener=fake_open)
        self.assertEqual(result, {"2026-01-01": "New Year's Day"})

    def test_connection_failure_is_handled(self):
        def fake_open(request, timeout):
            raise URLError("offline")
        with self.assertRaises(HolidayApiError):
            fetch_public_holidays(2026, opener=fake_open)

    def test_invalid_json_shape(self):
        def fake_open(request, timeout):
            return FakeResponse(b'{}')
        with self.assertRaises(HolidayApiError):
            fetch_public_holidays(2026, opener=fake_open)

    def test_year_validation(self):
        with self.assertRaises(ValueError):
            fetch_public_holidays("2026")


if __name__ == "__main__":
    unittest.main()
