"""Sunrise / sunset on the hub, no internet needed (ADR 0013).

Classic almanac algorithm (NOAA / "Almanac for Computers", zenith 90.833 deg incl.
refraction), accurate to about a minute at mid latitudes - enough for lights.
"""

import math
from datetime import date, datetime, time, timedelta, timezone
from typing import Optional, Tuple

ZENITH = 90.833


def _event(d: date, lat: float, lon: float, rising: bool) -> Optional[datetime]:
    n = d.timetuple().tm_yday
    lng_hour = lon / 15.0
    t = n + ((6 if rising else 18) - lng_hour) / 24.0
    m = 0.9856 * t - 3.289
    sl = (m + 1.916 * math.sin(math.radians(m)) + 0.020 * math.sin(math.radians(2 * m))
          + 282.634) % 360
    ra = math.degrees(math.atan(0.91764 * math.tan(math.radians(sl)))) % 360
    ra = (ra + (math.floor(sl / 90) * 90 - math.floor(ra / 90) * 90)) / 15.0
    sin_dec = 0.39782 * math.sin(math.radians(sl))
    cos_dec = math.cos(math.asin(sin_dec))
    cos_h = ((math.cos(math.radians(ZENITH)) - sin_dec * math.sin(math.radians(lat)))
             / (cos_dec * math.cos(math.radians(lat))))
    if cos_h > 1 or cos_h < -1:
        return None  # polar day/night: the sun does not rise or set
    h = (360 - math.degrees(math.acos(cos_h))) if rising else math.degrees(math.acos(cos_h))
    ut = (h / 15.0 + ra - 0.06571 * t - 6.622 - lng_hour) % 24
    out = datetime.combine(d, time(0), tzinfo=timezone.utc) + timedelta(hours=ut)
    # The local date d can map to the previous/next UTC day (e.g. Tashkent sunrise ~23:50 UTC).
    noon = datetime.combine(d, time(12), tzinfo=timezone.utc) - timedelta(hours=lng_hour)
    if out - noon > timedelta(hours=12):
        out -= timedelta(days=1)
    elif noon - out > timedelta(hours=12):
        out += timedelta(days=1)
    return out


def sun_times(d: date, lat: float, lon: float) -> Tuple[Optional[datetime], Optional[datetime]]:
    """(sunrise, sunset) in UTC for the LOCAL date d at (lat, lon)."""
    return _event(d, lat, lon, True), _event(d, lat, lon, False)
