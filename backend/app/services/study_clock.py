from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

def now():
    return datetime.now(timezone.utc)

def utc(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)

def study_date(value, name):
    try:
        zone = ZoneInfo(name or "UTC")
    except (ZoneInfoNotFoundError, ValueError):
        zone = ZoneInfo("UTC")
    return utc(value).astimezone(zone).date(), zone.key
