from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from datetime import time
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "config" / "preferences.toml"


@dataclass
class Preferences:
    levels: list[int] = field(default_factory=list)
    prefectures: list[str] = field(default_factory=list)
    cities: list[str] = field(default_factory=list)
    title_keywords: list[str] = field(default_factory=list)
    prefer_keywords: list[str] = field(default_factory=list)
    avoid_keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)
    preferred_age_decades: list[int] = field(default_factory=list)
    weeks_from: int = 1
    weeks: int = 2
    weekend_holiday_only: bool = True
    start_after: time | None = None
    start_before: time | None = None
    max_fee: int = 0
    top_n: int = 30
    level_tolerance: int = 1
    max_misses: int = 2
    max_details: int = 80
    other_min_score: int = 25
    max_places: int = 50
    places: list[str] = field(default_factory=list)


def _parse_time(s: str) -> time | None:
    return time.fromisoformat(s) if s else None


def load_preferences(path: Path = DEFAULT_PATH) -> Preferences:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    get = lambda section, key, default: raw.get(section, {}).get(key, default)  # noqa: E731
    return Preferences(
        levels=get("level", "levels", []),
        prefectures=get("area", "prefectures", []),
        cities=get("area", "cities", []),
        title_keywords=get("style", "title_keywords", []),
        prefer_keywords=get("style", "prefer_keywords", []),
        avoid_keywords=get("style", "avoid_keywords", []),
        exclude_keywords=get("style", "exclude_keywords", []),
        preferred_age_decades=get("people", "preferred_age_decades", []),
        weeks_from=get("schedule", "weeks_from", 1),
        weeks=get("schedule", "weeks", 2),
        weekend_holiday_only=get("schedule", "weekend_holiday_only", True),
        start_after=_parse_time(get("schedule", "start_after", "")),
        start_before=_parse_time(get("schedule", "start_before", "")),
        max_fee=get("budget", "max_fee", 0),
        top_n=get("output", "top_n", 30),
        level_tolerance=get("near_match", "level_tolerance", 1),
        max_misses=get("near_match", "max_misses", 2),
        max_details=get("fetch", "max_details", 80),
        other_min_score=get("recommend", "other_min_score", 25),
        max_places=get("fetch", "max_places", 50),
        places=get("fetch", "places", []),
    )
