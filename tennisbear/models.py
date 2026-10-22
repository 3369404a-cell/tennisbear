from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Event:
    """取得元に依存しない、正規化済みのイベント。"""

    id: str
    title: str
    url: str  # テニスベアのイベント詳細ページ（申込はここから）
    start: datetime
    end: datetime | None = None
    prefecture: str = ""
    city: str = ""
    venue: str = ""
    place_code: str = ""
    weekend_or_holiday: bool | None = None  # テニスベア側の土日祝フラグ
    level_min: int | None = None  # ベアレベル 1〜9
    level_max: int | None = None
    description: str = ""
    tags: list[str] = field(default_factory=list)  # 例: 練習多め, シングルス
    fee: int | None = None  # 円
    capacity: int | None = None
    remaining: int | None = None  # 残り枠
    organizer_age_decade: int | None = None  # 20, 30, ...
    participant_age_decades: list[int] = field(default_factory=list)
    participant_levels: list[int] = field(default_factory=list)  # 参加者のベアレベル
    participants: int | None = None  # 現在の参加人数
    men: int | None = None
    women: int | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["start"] = self.start.isoformat()
        d["end"] = self.end.isoformat() if self.end else None
        return d

    @classmethod
    def from_dict(cls, d: dict) -> Event:
        d = dict(d)
        d["start"] = datetime.fromisoformat(d["start"])
        d["end"] = datetime.fromisoformat(d["end"]) if d.get("end") else None
        return cls(**d)


def load_events(path: Path) -> list[Event]:
    return [Event.from_dict(d) for d in json.loads(path.read_text(encoding="utf-8"))]


def save_events(events: list[Event], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([e.to_dict() for e in events], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
