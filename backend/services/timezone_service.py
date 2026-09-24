from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Dict, Any, Tuple, Optional

# Canonical country to IANA timezone mapping
COUNTRY_TIMEZONE_MAP: Dict[str, str] = {
    "India": "Asia/Kolkata",
    "CzechRepublic": "Europe/Prague",
    "Czech Republic": "Europe/Prague",
    "Albania": "Europe/Tirane",
    "Andorra": "Europe/Andorra",
    "Armenia": "Asia/Yerevan",
    "Austria": "Europe/Vienna",
    "Azerbaijan": "Asia/Baku",
    "Belarus": "Europe/Minsk",
    "Belgium": "Europe/Brussels",
    "BosniaAndHerzegovina": "Europe/Sarajevo",
    "Bosnia and Herzegovina": "Europe/Sarajevo",
    "Bulgaria": "Europe/Sofia",
    "Croatia": "Europe/Zagreb",
    "Cyprus": "Asia/Nicosia",
    "Denmark": "Europe/Copenhagen",
    "Estonia": "Europe/Tallinn",
    "Finland": "Europe/Helsinki",
    "France": "Europe/Paris",
    "Georgia": "Asia/Tbilisi",
    "Germany": "Europe/Berlin",
    "Greece": "Europe/Athens",
    "Hungary": "Europe/Budapest",
    "Iceland": "Atlantic/Reykjavik",
    "Ireland": "Europe/Dublin",
    "Italy": "Europe/Rome",
    "Kosovo": "Europe/Belgrade",
    "Latvia": "Europe/Riga",
    "Liechtenstein": "Europe/Vaduz",
    "Lithuania": "Europe/Vilnius",
    "Luxembourg": "Europe/Luxembourg",
    "Malta": "Europe/Malta",
    "Moldova": "Europe/Chisinau",
    "Monaco": "Europe/Monaco",
    "Montenegro": "Europe/Podgorica",
    "Netherlands": "Europe/Amsterdam",
    "NorthMacedonia": "Europe/Skopje",
    "North Macedonia": "Europe/Skopje",
    "Norway": "Europe/Oslo",
    "Poland": "Europe/Warsaw",
    "Portugal": "Europe/Lisbon",
    "Romania": "Europe/Bucharest",
    "Russia": "Europe/Moscow",
    "SanMarino": "Europe/San_Marino",
    "San Marino": "Europe/San_Marino",
    "Serbia": "Europe/Belgrade",
    "Slovakia": "Europe/Bratislava",
    "Slovenia": "Europe/Ljubljana",
    "Spain": "Europe/Madrid",
    "Sweden": "Europe/Stockholm",
    "Switzerland": "Europe/Zurich",
    "Turkey": "Europe/Istanbul",
    "Ukraine": "Europe/Kyiv",
    "UnitedKingdom": "Europe/London",
    "United Kingdom": "Europe/London",
    "UK": "Europe/London",
    "VaticanCity": "Europe/Vatican",
    "UnitedStates": "America/New_York",
    "United States": "America/New_York",
    "USA": "America/New_York",
    "US": "America/New_York",
}

class TimezoneService:
    @staticmethod
    def get_timezone_for_country(country: str) -> str:
        if not country:
            return "UTC"
        # 1. Exact or case-insensitive match
        for k, tz in COUNTRY_TIMEZONE_MAP.items():
            if k.lower() == country.strip().lower():
                return tz
        # 2. Alphanumeric normalized match
        clean_search = "".join(c.lower() for c in country if c.isalnum())
        for k, tz in COUNTRY_TIMEZONE_MAP.items():
            clean_k = "".join(c.lower() for c in k if c.isalnum())
            if clean_k == clean_search:
                return tz
        return "UTC"

    @staticmethod
    def is_dst_active(tz_or_country: str, target_date: Optional[date] = None) -> Tuple[bool, float]:
        """Calculates (is_dst, offset_hours) for a timezone or country on target_date."""
        check_date = target_date or date.today()
        tz_name = tz_or_country if "/" in tz_or_country else TimezoneService.get_timezone_for_country(tz_or_country)
        try:
            tz = ZoneInfo(tz_name)
            dt = datetime(check_date.year, check_date.month, check_date.day, 12, 0, tzinfo=tz)
            dst_offset = dt.dst()
            is_dst = dst_offset is not None and dst_offset.total_seconds() != 0
            utc_offset = dt.utcoffset()
            offset_hours = (utc_offset.total_seconds() / 3600.0) if utc_offset else 0.0
            return is_dst, offset_hours
        except Exception:
            return False, 0.0

    @staticmethod
    def get_timezone_info(country: str, target_date: Optional[date] = None) -> Dict[str, Any]:
        """
        Calculates timezone, current UTC offset, and whether Daylight Saving Time (DST)
        is active on the specified target_date.
        """
        tz_name = TimezoneService.get_timezone_for_country(country)
        check_date = target_date or date.today()
        
        try:
            tz = ZoneInfo(tz_name)
            # Sample at 12:00 noon on target date
            dt = datetime(check_date.year, check_date.month, check_date.day, 12, 0, tzinfo=tz)
            dst_offset = dt.dst()
            is_dst = dst_offset is not None and dst_offset.total_seconds() != 0
            utc_offset = dt.utcoffset()
            offset_hours = (utc_offset.total_seconds() / 3600.0) if utc_offset else 0.0

            # Format UTC string e.g. "UTC+05:30" or "UTC+02:00"
            sign = "+" if offset_hours >= 0 else "-"
            abs_hours = abs(int(offset_hours))
            abs_mins = int(abs(offset_hours - int(offset_hours)) * 60)
            offset_str = f"UTC{sign}{abs_hours:02d}:{abs_mins:02d}"

            return {
                "country": country,
                "timezone": tz_name,
                "target_date": check_date.isoformat(),
                "is_dst_active": is_dst,
                "utc_offset_hours": offset_hours,
                "utc_offset_str": offset_str,
                "tz_abbreviation": dt.tzname(),
            }
        except Exception as e:
            return {
                "country": country,
                "timezone": "UTC",
                "target_date": check_date.isoformat(),
                "is_dst_active": False,
                "utc_offset_hours": 0.0,
                "utc_offset_str": "UTC+00:00",
                "tz_abbreviation": "UTC",
            }

    @staticmethod
    def calculate_shift_overlap(
        sme_country: str,
        receiver_country: str,
        target_date: Optional[date] = None,
        sme_shift_start: Any = time(8, 0),
        sme_shift_end: Any = time(17, 0),
        receiver_shift_start: Any = time(8, 0),
        receiver_shift_end: Any = time(17, 0),
    ) -> Dict[str, Any]:
        """
        Converts SME local shift and Receiver local shift on target_date to UTC,
        computes overlap in UTC, and translates overlap back to both local times.
        Takes full account of Daylight Saving Time changes on target_date!
        """
        check_date = target_date or date.today()

        # Parse string times if provided
        if isinstance(sme_shift_start, str):
            parts = [int(p) for p in sme_shift_start.split(":")]
            sme_shift_start = time(parts[0], parts[1])
        if isinstance(sme_shift_end, str):
            parts = [int(p) for p in sme_shift_end.split(":")]
            sme_shift_end = time(parts[0], parts[1])
        if isinstance(receiver_shift_start, str):
            parts = [int(p) for p in receiver_shift_start.split(":")]
            receiver_shift_start = time(parts[0], parts[1])
        if isinstance(receiver_shift_end, str):
            parts = [int(p) for p in receiver_shift_end.split(":")]
            receiver_shift_end = time(parts[0], parts[1])

        sme_tz_name = TimezoneService.get_timezone_for_country(sme_country)
        rcv_tz_name = TimezoneService.get_timezone_for_country(receiver_country)

        sme_tz = ZoneInfo(sme_tz_name)
        rcv_tz = ZoneInfo(rcv_tz_name)

        # Build timezone-aware datetimes for SME shift
        sme_start_local = datetime.combine(check_date, sme_shift_start, tzinfo=sme_tz)
        sme_end_local = datetime.combine(check_date, sme_shift_end, tzinfo=sme_tz)
        sme_start_utc = sme_start_local.astimezone(timezone.utc)
        sme_end_utc = sme_end_local.astimezone(timezone.utc)

        # Build timezone-aware datetimes for Receiver shift
        rcv_start_local = datetime.combine(check_date, receiver_shift_start, tzinfo=rcv_tz)
        rcv_end_local = datetime.combine(check_date, receiver_shift_end, tzinfo=rcv_tz)
        rcv_start_utc = rcv_start_local.astimezone(timezone.utc)
        rcv_end_utc = rcv_end_local.astimezone(timezone.utc)

        # Calculate UTC overlap
        overlap_start_utc = max(sme_start_utc, rcv_start_utc)
        overlap_end_utc = min(sme_end_utc, rcv_end_utc)

        has_overlap = overlap_start_utc < overlap_end_utc
        overlap_duration_hours = 0.0
        if has_overlap:
            overlap_duration_hours = round((overlap_end_utc - overlap_start_utc).total_seconds() / 3600.0, 2)

        # Convert overlap to local times
        sme_overlap_start = overlap_start_utc.astimezone(sme_tz).time() if has_overlap else None
        sme_overlap_end = overlap_end_utc.astimezone(sme_tz).time() if has_overlap else None

        rcv_overlap_start = overlap_start_utc.astimezone(rcv_tz).time() if has_overlap else None
        rcv_overlap_end = overlap_end_utc.astimezone(rcv_tz).time() if has_overlap else None

        # Info on DST for both
        sme_info = TimezoneService.get_timezone_info(sme_country, check_date)
        rcv_info = TimezoneService.get_timezone_info(receiver_country, check_date)

        return {
            "target_date": check_date.isoformat(),
            "has_overlap": has_overlap,
            "overlap_hours": overlap_duration_hours,
            "sme_country": sme_country,
            "receiver_country": receiver_country,
            "sme_timezone": sme_tz_name,
            "receiver_timezone": rcv_tz_name,
            "sme_dst_active": sme_info["is_dst_active"],
            "receiver_dst_active": rcv_info["is_dst_active"],
            "sme_utc_offset": sme_info["utc_offset_str"],
            "receiver_utc_offset": rcv_info["utc_offset_str"],
            "overlap_window_sme": f"{sme_overlap_start.strftime('%H:%M')} - {sme_overlap_end.strftime('%H:%M')}" if has_overlap else None,
            "overlap_window_receiver": f"{rcv_overlap_start.strftime('%H:%M')} - {rcv_overlap_end.strftime('%H:%M')}" if has_overlap else None,
            "sme": {
                "country": sme_country,
                "timezone": sme_tz_name,
                "is_dst": sme_info["is_dst_active"],
                "utc_offset": sme_info["utc_offset_str"],
                "shift_start": sme_shift_start.strftime("%H:%M"),
                "shift_end": sme_shift_end.strftime("%H:%M"),
                "overlap_start_local": sme_overlap_start.strftime("%H:%M") if sme_overlap_start else None,
                "overlap_end_local": sme_overlap_end.strftime("%H:%M") if sme_overlap_end else None,
            },
            "receiver": {
                "country": receiver_country,
                "timezone": rcv_tz_name,
                "is_dst": rcv_info["is_dst_active"],
                "utc_offset": rcv_info["utc_offset_str"],
                "shift_start": receiver_shift_start.strftime("%H:%M"),
                "shift_end": receiver_shift_end.strftime("%H:%M"),
                "overlap_start_local": rcv_overlap_start.strftime("%H:%M") if rcv_overlap_start else None,
                "overlap_end_local": rcv_overlap_end.strftime("%H:%M") if rcv_overlap_end else None,
            },
            "overlap_start_utc": overlap_start_utc.strftime("%H:%M") if has_overlap else None,
            "overlap_end_utc": overlap_end_utc.strftime("%H:%M") if has_overlap else None,
        }
