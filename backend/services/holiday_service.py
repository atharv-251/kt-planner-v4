import json
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from backend.config import HOLIDAYS_JSON_PATH

class HolidayService:
    """
    Authoritative single-source holiday service.
    Exclusively loads BankHolidays from holidays.json.
    Zero holiday dates may be hardcoded in Python.
    """
    _instance: Optional["HolidayService"] = None
    _holidays_cache: Optional[Dict[str, Dict[str, str]]] = None

    def __init__(self, json_path: Optional[Path] = None):
        self.json_path = json_path or HOLIDAYS_JSON_PATH
        self._load_cache()

    @classmethod
    def get_instance(cls) -> "HolidayService":
        if cls._instance is None:
            cls._instance = HolidayService()
        return cls._instance

    def _load_cache(self) -> None:
        if not self.json_path.exists():
            raise FileNotFoundError(f"Authoritative holidays.json not found at {self.json_path}")
        
        with open(self.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # The structure is {"BankHolidays": {"India": {"YYYY-MM-DD": "Name"}, ...}}
            self._holidays_cache = data.get("BankHolidays", {})

    def reload(self) -> None:
        self._load_cache()

    def get_supported_countries(self) -> List[str]:
        if self._holidays_cache is None:
            self._load_cache()
        return sorted(list(self._holidays_cache.keys()))

    def get_holidays_for_country(self, country: str) -> Dict[str, str]:
        if self._holidays_cache is None:
            self._load_cache()
        # Normalization for country lookup
        for key in self._holidays_cache:
            if key.lower() == country.strip().lower():
                return self._holidays_cache[key]
        return {}

    def is_holiday(self, country: str, check_date: date) -> Tuple[bool, Optional[str]]:
        date_str = check_date.strftime("%Y-%m-%d")
        country_holidays = self.get_holidays_for_country(country)
        if date_str in country_holidays:
            return True, country_holidays[date_str]
        return False, None

    @staticmethod
    def is_weekend(check_date: date) -> bool:
        # Monday is 0, Sunday is 6. Weekend is Saturday (5) and Sunday (6).
        return check_date.weekday() in (5, 6)

    def is_working_day(self, country: str, check_date: date) -> bool:
        if self.is_weekend(check_date):
            return False
        is_hol, _ = self.is_holiday(country, check_date)
        return not is_hol

    def get_working_days(self, country: str, start_date: date, end_date: date) -> List[date]:
        working_days = []
        cur = start_date
        while cur <= end_date:
            if self.is_working_day(country, cur):
                working_days.append(cur)
            cur += timedelta(days=1)
        return working_days

    def get_holidays_in_range(self, country: str, start_date: date, end_date: date) -> Dict[str, str]:
        holidays_in_range = {}
        cur = start_date
        while cur <= end_date:
            is_hol, name = self.is_holiday(country, cur)
            if is_hol and name:
                holidays_in_range[cur.strftime("%Y-%m-%d")] = name
            cur += timedelta(days=1)
        return holidays_in_range

