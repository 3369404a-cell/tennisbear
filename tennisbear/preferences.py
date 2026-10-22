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
    prefer_keywords: list[str] = field(default_factory=list)
    avoid_keywords: list[str] = field(default_factory=list)
    exclude_keywords: list[str] = field(default_factory=list)
    preferred_age_decades: list[int] = field(default_factory=list)
    days_ahead: int = 14
    weekdays: list[int] = field(default_factory=list)
    start_after: time | None = None
    start_before: time | None = None
    max_fee: int = 0
    top_n: int = 30


def _parse_time(s: str) -> time | None:
    return time.fromisoformat(s) if s else None


def load_preferences(path: Path = DEFAULT_PATH) -> Preferences:
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    get = lambda section, key, default: raw.get(section, {}).get(key, default)  # noqa: E731
    return Preferences(
        levels=get("level", "levels", []),
        prefectures=get("area", "prefectures", []),
        cities=get("area", "cities", []),
        prefer_keywords=get("style", "prefer_keywords", []),
        avoid_keywords=get("style", "avoid_keywords", []),
        exclude_keywords=get("style", "exclude_keywords", []),
        preferred_age_decades=get("people", "preferred_age_decades", []),
        days_ahead=get("schedule", "days_ahead", 14),
        weekdays=get("schedule", "weekdays", []),
        start_after=_parse_time(get("schedule", "start_after", "")),
        start_before=_parse_time(get("schedule", "start_before", "")),
        max_fee=get("budget", "max_fee", 0),
        top_n=get("output", "top_n", 30),
    )
