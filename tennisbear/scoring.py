from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .models import Event
from .preferences import Preferences


@dataclass
class Recommendation:
    event: Event
    score: int
    reasons: list[str] = field(default_factory=list)


def _text(event: Event) -> str:
    return "\n".join([event.title, " ".join(event.tags), event.description])


def passes_list_filters(event: Event, prefs: Preferences) -> bool:
    """一覧ページの情報だけで判定できる必須条件（詳細ページを開く前に使う）。"""
    if prefs.prefectures and event.prefecture not in prefs.prefectures:
        return False
    if prefs.cities and event.city not in prefs.cities:
        return False
    if prefs.levels and event.level_min is not None and event.level_max is not None:
        if not any(event.level_min <= lv <= event.level_max for lv in prefs.levels):
            return False
    if prefs.weekdays and event.start.weekday() not in prefs.weekdays:
        return False
    if prefs.start_after and event.start.time() < prefs.start_after:
        return False
    if prefs.start_before and event.start.time() > prefs.start_before:
        return False
    return True


def is_candidate(event: Event, prefs: Preferences, now: datetime) -> bool:
    """必須条件。ここで落ちたイベントは一覧に出さない。"""
    if not (now <= event.start <= now + timedelta(days=prefs.days_ahead)):
        return False
    if not passes_list_filters(event, prefs):
        return False
    if event.remaining is not None and event.remaining <= 0:
        return False
    if prefs.max_fee and event.fee is not None and event.fee > prefs.max_fee:
        return False
    text = _text(event)
    if any(k in text for k in prefs.exclude_keywords):
        return False
    return True


def score(event: Event, prefs: Preferences) -> Recommendation:
    text = _text(event)
    points = 0
    reasons: list[str] = []

    hits = [k for k in prefs.prefer_keywords if k in text]
    if hits:
        points += 10 * len(hits)
        reasons.append("・".join(hits))

    avoids = [k for k in prefs.avoid_keywords if k in text]
    points -= 15 * len(avoids)

    decades = set(prefs.preferred_age_decades)
    if decades and event.organizer_age_decade in decades:
        points += 15
        reasons.append(f"主催{event.organizer_age_decade}代")
    if decades and event.participant_age_decades:
        share = sum(d in decades for d in event.participant_age_decades) / len(
            event.participant_age_decades
        )
        points += round(20 * share)
        if share >= 0.5:
            reasons.append("参加者20〜30代中心" if decades == {20, 30} else "参加者の年代が近い")

    if event.level_min is not None and event.level_max is not None and prefs.levels:
        # 対象レベルの幅が狭く、希望レベルにぴったりなほど加点
        width = event.level_max - event.level_min + 1
        points += max(0, 6 - width)
        reasons.append(f"Lv{event.level_min}〜{event.level_max}")

    if event.remaining is not None and event.remaining <= 2:
        reasons.append(f"残り{event.remaining}枠")

    return Recommendation(event=event, score=points, reasons=reasons)


def recommend(events: list[Event], prefs: Preferences, now: datetime) -> list[Recommendation]:
    recs = [score(e, prefs) for e in events if is_candidate(e, prefs, now)]
    recs.sort(key=lambda r: (-r.score, r.event.start))
    return recs[: prefs.top_n]
