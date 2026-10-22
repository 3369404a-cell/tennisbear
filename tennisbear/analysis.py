"""イベントの参加者構成をまとめる。"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .models import Event
from .preferences import Preferences


@dataclass
class ParticipantAnalysis:
    lines: list[str] = field(default_factory=list)  # 人数・男女・年代・レベルの内訳
    comment: str = ""  # ひとことまとめ


def _counts(values: list[int], fmt) -> str:
    return " ".join(f"{fmt(v)}×{n}" for v, n in sorted(Counter(values).items()))


def analyze(event: Event, prefs: Preferences) -> ParticipantAnalysis:
    a = ParticipantAnalysis()
    count = event.participants
    if count is not None and event.capacity:
        left = f"（残り{event.remaining}）" if event.remaining is not None else ""
        a.lines.append(f"参加 {count}/{event.capacity}名{left}")
    if event.men is not None and event.women is not None and (event.men or event.women):
        a.lines.append(f"男性{event.men}・女性{event.women}")

    ages = event.participant_age_decades
    decades = set(prefs.preferred_age_decades)
    age_share = None
    if ages:
        age_share = sum(d in decades for d in ages) / len(ages) if decades else None
        share = f"（希望年代 {age_share:.0%}）" if age_share is not None else ""
        a.lines.append(f"年代: {_counts(ages, lambda d: f'{d}代')}{share}")

    levels = event.participant_levels
    avg = None
    if levels:
        avg = sum(levels) / len(levels)
        a.lines.append(f"レベル: {_counts(levels, lambda lv: f'Lv{lv}')}（平均{avg:.1f}）")

    comments = []
    if count is not None and count <= 1:
        comments.append("まだ主催者だけ。これから集まる段階")
    if age_share is not None and len(ages) >= 2:
        if age_share >= 0.7:
            comments.append("同年代が中心")
        elif age_share < 0.3:
            comments.append("年上の参加者が多め" if min(ages) >= max(decades) else "年代が離れた参加者が多め")
    if avg is not None and prefs.levels:
        lo, hi = min(prefs.levels), max(prefs.levels)
        if avg > hi + 0.5:
            comments.append("参加者のレベルは高め")
        elif avg < lo - 0.5:
            comments.append("参加者のレベルは低め")
        elif len(levels) >= 2:
            comments.append("レベルが近い人が多い")
    if event.men is not None and event.women is not None and event.men + event.women >= 3:
        if min(event.men, event.women) == 0:
            comments.append("男性のみ" if event.women == 0 else "女性のみ")
    a.comment = "、".join(comments)
    return a
