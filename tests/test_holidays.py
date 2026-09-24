from datetime import date
from backend.services.holiday_service import HolidayService

def test_holiday_service_loads_from_json():
    svc = HolidayService.get_instance()
    countries = svc.get_supported_countries()
    assert "India" in countries
    assert "CzechRepublic" in countries
    assert len(countries) >= 30

def test_india_holidays():
    svc = HolidayService.get_instance()
    # Republic Day: 2026-01-26
    is_hol, name = svc.is_holiday("India", date(2026, 1, 26))
    assert is_hol is True
    assert "Republic Day" in name

    # Gandhi Jayanti: 2026-10-02
    is_hol, name = svc.is_holiday("India", date(2026, 10, 2))
    assert is_hol is True
    assert "Gandhi" in name

def test_czech_holidays():
    svc = HolidayService.get_instance()
    # Good Friday: 2026-04-03
    is_hol, name = svc.is_holiday("CzechRepublic", date(2026, 4, 3))
    assert is_hol is True
    assert "Good Friday" in name

def test_weekend_and_working_day():
    svc = HolidayService.get_instance()
    # 2026-09-20 is Sunday
    sunday = date(2026, 9, 20)
    assert svc.is_weekend(sunday) is True
    assert svc.is_working_day("India", sunday) is False

    # 2026-09-21 is Monday (Regular working day in India)
    monday = date(2026, 9, 21)
    assert svc.is_weekend(monday) is False
    assert svc.is_working_day("India", monday) is True

    # 2026-10-02 is Friday (Gandhi Jayanti Bank Holiday)
    friday_holiday = date(2026, 10, 2)
    assert svc.is_weekend(friday_holiday) is False
    assert svc.is_working_day("India", friday_holiday) is False

