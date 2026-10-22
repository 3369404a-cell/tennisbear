"""土日祝の判定と、「来週・再来週」の期間計算。"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

FIXED = {(1, 1), (2, 11), (2, 23), (4, 29), (5, 3), (5, 4), (5, 5), (8, 11), (11, 3), (11, 23)}
# (月, 第n月曜日)
HAPPY_MONDAYS = {(1, 2), (7, 3), (9, 3), (10, 2)}


def _nth_monday(year: int, month: int, n: int) -> date:
    first = date(year, month, 1)
    return first + timedelta(days=(7 - first.weekday()) % 7 + 7 * (n - 1))


def _equinoxes(year: int) -> set[date]:
    # 1980〜2099年で使える近似式
    spring = int(20.8431 + 0.242194 * (year - 1980) - (year - 1980) // 4)
    autumn = int(23.2488 + 0.242194 * (year - 1980) - (year - 1980) // 4)
    return {date(year, 3, spring), date(year, 9, autumn)}


def _base_holidays(year: int) -> set[date]:
    days = {date(year, m, d) for m, d in FIXED}
    days |= {_nth_monday(year, m, n) for m, n in HAPPY_MONDAYS}
    days |= _equinoxes(year)
    return days


def holidays(year: int) -> set[date]:
    base = _base_holidays(year)
    result = set(base)
    for d in sorted(base):
        if d.weekday() == 6:  # 振替休日: 日曜の祝日の後の最初の平日
            sub = d + timedelta(days=1)
            while sub in base:
                sub += timedelta(days=1)
            result.add(sub)
    for d in sorted(base):  # 国民の休日: 祝日に挟まれた平日
        mid = d + timedelta(days=1)
        if mid not in result and mid + timedelta(days=1) in base and mid.weekday() != 6:
            result.add(mid)
    return result


def is_weekend_or_holiday(d: date) -> bool:
    return d.weekday() >= 5 or d in holidays(d.year)


def week_window(now: datetime, weeks_from: int, weeks: int) -> tuple[datetime, datetime]:
    """weeks_from 週後の月曜 0:00 から weeks 週間。来週と再来週なら (1, 2)。"""
    monday = now.date() - timedelta(days=now.weekday()) + timedelta(weeks=weeks_from)
    start = datetime.combine(monday, time())
    return start, start + timedelta(weeks=weeks)
