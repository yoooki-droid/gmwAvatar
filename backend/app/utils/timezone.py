from datetime import datetime
from zoneinfo import ZoneInfo

from ..config import settings


def now_local_naive() -> datetime:
    """返回中国时区当前时间（去除 tzinfo，便于 MySQL/SQLite 统一存储）。"""
    tz = ZoneInfo(settings.timezone)
    return datetime.now(tz).replace(tzinfo=None)
