from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .calendar_jp import is_weekend_or_holiday, week_window
from .models import Event
from .preferences import Preferences

TITLE = "title"  # イベント名にラリー・練習系の文言がある
OTHER = "other"  # 名前にはないが条件的におすすめ


@dataclass
class Recommendation:
    event: Event
    score: int
    category: str = TITLE
    reasons: list[str] = field(default_factory=list)
    misses: list[str] = field(default_factory=list)  # 満たしていない希望条件

    @property
    def exact(self) -> bool:
        return not self.misses


def level_distance(event: Event, prefs: Preferences) -> int:
    """希望レベルとイベント対象レベルの離れ具合。重なっていれば0。不明も0扱い。"""
    if not prefs.levels or event.level_min is None or event.level_max is None:
        return 0
    return min(max(event.level_min - lv, lv - event.level_max, 0) for lv in prefs.levels)


def is_weekend_event(event: Event) -> bool:
    if event.weekend_or_holiday is not None:
        return event.weekend_or_holiday or is_weekend_or_holiday(event.start.date())
    return is_weekend_or_holiday(event.start.date())


def title_hits(event: Event, prefs: Preferences) -> list[str]:
    return [k for k in prefs.title_keywords if k in event.title]


def passes_list_filters(event: Event, prefs: Preferences, now: datetime) -> bool:
    """一覧ページの情報だけで判定できる必須条件（詳細ページを開く前に使う）。"""
    start, end = week_window(now, prefs.weeks_from, prefs.weeks)
    if not (start <= event.start < end and event.start >= now):
        return False
    if prefs.weekend_holiday_only and not is_weekend_event(event):
        return False
    if prefs.prefectures and event.prefecture not in prefs.prefectures:
        return False
    if prefs.cities and event.city not in prefs.cities:
        return False
    if level_distance(event, prefs) > prefs.level_tolerance:
        return False
    if prefs.start_after and event.start.time() < prefs.start_after:
        return False
    if prefs.start_before and event.start.time() > prefs.start_before:
        return False
    return True


def is_candidate(event: Event, prefs: Preferences, now: datetime) -> bool:
    """必須条件。ここで落ちたイベントは一覧に出さない。"""
    if not passes_list_filters(event, prefs, now):
        return False
    if event.remaining is not None and event.remaining <= 0:
        return False
    if prefs.max_fee and event.fee is not None and event.fee > prefs.max_fee:
        return False
    text = "\n".join([event.title, " ".join(event.tags), event.description])
    return not any(k in text for k in prefs.exclude_keywords)


def score(event: Event, prefs: Preferences) -> Recommendation:
    points = 0
    reasons: list[str] = []
    misses: list[str] = []

    if level_distance(event, prefs):
        misses.append(f"Lv{event.level_min}〜{event.level_max}（希望Lv{'・'.join(map(str, prefs.levels))}）")
    elif event.level_min is not None and event.level_max is not None:
        # 対象レベルの幅が狭く、希望レベルにぴったりなほど加点
        points += 5 + max(0, 6 - (event.level_max - event.level_min + 1))
        reasons.append(f"Lv{event.level_min}〜{event.level_max}")

    in_title = title_hits(event, prefs)
    if in_title:
        points += 20
        reasons.append("名前に「" + "」「".join(in_title) + "」")
    body = "\n".join([" ".join(event.tags), event.description])
    in_body = [k for k in prefs.prefer_keywords if k in body and k not in in_title]
    if in_body:
        points += 8 * min(len(in_body), 3)
        reasons.append("・".join(in_body[:4]))
    if not in_title and not in_body and prefs.prefer_keywords:
        misses.append("練習系の記載なし")
    points -= 15 * sum(k in f"{event.title}\n{body}" for k in prefs.avoid_keywords)

    decades = set(prefs.preferred_age_decades)
    age_known = age_ok = False
    if decades and event.organizer_age_decade is not None:
        age_known = True
        if event.organizer_age_decade in decades:
            age_ok = True
            points += 15
            reasons.append(f"主催{event.organizer_age_decade}代")
    if decades and event.participant_age_decades:
        age_known = True
        share = sum(d in decades for d in event.participant_age_decades) / len(
            event.participant_age_decades
        )
        points += round(20 * share)
        if share >= 0.5:
            age_ok = True
            reasons.append("参加者20〜30代中心" if decades == {20, 30} else "参加者の年代が近い")
    if age_known and not age_ok:
        misses.append("年代が希望と違う")

    if event.remaining is not None and event.remaining <= 2:
        reasons.append(f"残り{event.remaining}枠")

    points -= 20 * len(misses)
    return Recommendation(
        event=event,
        score=points,
        category=TITLE if in_title else OTHER,
        reasons=reasons,
        misses=misses,
    )


def recommend(events: list[Event], prefs: Preferences, now: datetime) -> list[Recommendation]:
    """イベント名がラリー・練習系のものは日付順で全部、それ以外はおすすめ度の高いものだけ。"""
    recs = [score(e, prefs) for e in events if is_candidate(e, prefs, now)]
    titled = [r for r in recs if r.category == TITLE and len(r.misses) <= prefs.max_misses]
    others = [
        r for r in recs
        if r.category == OTHER and r.score >= prefs.other_min_score and len(r.misses) <= 1
    ]
    titled.sort(key=lambda r: (r.event.start, -r.score))
    others.sort(key=lambda r: (-r.score, r.event.start))
    return titled[: prefs.top_n] + others[: prefs.top_n]
