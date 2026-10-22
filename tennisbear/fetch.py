"""テニスベアの公開ページからイベントを取得して Event に正規化する。

- robots.txt で /api/ が禁止されているため、公開 HTML ページだけを読む。
- robots.txt の Crawl-delay: 10 に合わせ、リクエスト間隔を10秒空ける。
- 都道府県別の一覧には開始が近い順に40件だけしか載らないため、
  会場ごとの一覧（/place/{コード}/events）も巡回して先の日程を拾う。
  巡回する会場は設定の places と、都道府県一覧で見つかった会場。
- 一覧で必須条件に合うものだけ詳細ページを開き、参加者・料金・本文を取る。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from .models import Event
from .preferences import Preferences
from .scoring import level_distance, passes_list_filters, title_hits

BASE = "https://www.tennisbear.net"
USER_AGENT = "Mozilla/5.0 (compatible; personal-event-digest)"
CRAWL_DELAY = 10
NUXT_SCRIPT = Path(__file__).with_name("nuxt_state.js")

PREFECTURES = [
    "北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県", "福島県",
    "茨城県", "栃木県", "群馬県", "埼玉県", "千葉県", "東京都", "神奈川県",
    "新潟県", "富山県", "石川県", "福井県", "山梨県", "長野県", "岐阜県",
    "静岡県", "愛知県", "三重県", "滋賀県", "京都府", "大阪府", "兵庫県",
    "奈良県", "和歌山県", "鳥取県", "島根県", "岡山県", "広島県", "山口県",
    "徳島県", "香川県", "愛媛県", "高知県", "福岡県", "佐賀県", "長崎県",
    "熊本県", "大分県", "宮崎県", "鹿児島県", "沖縄県",
]
# テニスベアの都道府県コードは JIS の都道府県番号（例: 神奈川県 = pref14）
PREFECTURE_CODES = {name: f"pref{i}" for i, name in enumerate(PREFECTURES, start=1)}


class Client:
    def __init__(self, delay: float = CRAWL_DELAY):
        self.delay = delay
        self._last = 0.0

    def get(self, path: str) -> str:
        wait = self._last + self.delay - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(BASE + path, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return res.read().decode("utf-8", "replace")
        finally:
            self._last = time.monotonic()


def nuxt_state(html: str) -> dict:
    out = subprocess.run(
        ["node", str(NUXT_SCRIPT)], input=html, capture_output=True, text=True, check=True
    )
    return json.loads(out.stdout)


def _dt(s: str | None) -> datetime | None:
    # "2026-10-23T06:00:00.000+09:00" → 日本時間・タイムゾーンなし
    return datetime.fromisoformat(s).replace(tzinfo=None) if s else None


def _decade(age_name: str | None) -> int | None:
    m = re.match(r"(\d+)代", age_name or "")
    return int(m.group(1)) if m else None


def _city(address: str, prefecture: str) -> str:
    rest = address.split(prefecture, 1)[1] if prefecture and prefecture in address else ""
    m = re.match(r"(.+?[市区町村])", rest)
    return m.group(1) if m else ""


AGE_COUNT_KEYS = {
    "aboutAgeTenCount": 10, "aboutAgeTwentyCount": 20, "aboutAgeThirtyCount": 30,
    "aboutAgeFortyCount": 40, "aboutAgeFiftyCount": 50, "aboutAgeSixtyCount": 60,
    "aboutAgeSeventyCount": 70,
}
LEVEL_COUNT_KEYS = {
    f"level{name}Count": lv
    for lv, name in enumerate(
        ["One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"], start=1
    )
}


def _expand(counts: dict, keys: dict[str, int]) -> list[int]:
    return [value for key, value in keys.items() for _ in range(counts.get(key) or 0)]


def event_from_list_item(item: dict) -> Event:
    place = item.get("place") or {}
    prefecture = ((place.get("area") or {}).get("prefecture") or {}).get("name", "")
    address = place.get("address") or ""
    return Event(
        id=str(item["id"]),
        title=item.get("eventTitle", ""),
        url=f"{BASE}/event/{item['id']}/info",
        start=_dt(item["startDatetimeString"]),
        prefecture=prefecture,
        city=_city(address, prefecture),
        venue=place.get("name", ""),
        place_code=str(place.get("code") or ""),
        weekend_or_holiday=item.get("weekendOrHolidayFlg"),
        level_min=(item.get("minLevel") or {}).get("id"),
        level_max=(item.get("maxLevel") or {}).get("id"),
    )


def apply_detail(event: Event, detail: dict) -> Event:
    event.end = _dt(detail.get("endDateTime"))
    event.description = detail.get("eventContents") or ""
    event.tags = [t["name"] for t in detail.get("eventTagList") or []]
    event.fee = detail.get("priceOverview")
    event.capacity = detail.get("maxParticipantsNumber")
    event.participants = detail.get("nowParticipantsNumber")
    if event.capacity is not None and event.participants is not None:
        event.remaining = event.capacity - event.participants
    event.organizer_age_decade = _decade(((detail.get("organizer") or {}).get("age") or {}).get("name"))
    info = detail.get("participantInfo") or {}
    event.participant_age_decades = _expand(info.get("aboutAgeInfo") or {}, AGE_COUNT_KEYS)
    event.participant_levels = _expand(info.get("levelInfo") or {}, LEVEL_COUNT_KEYS)
    gender = info.get("genderInfo") or {}
    event.men, event.women = gender.get("menCount"), gender.get("womenCount")
    if detail.get("weekendOrHolidayFlg") is not None:
        event.weekend_or_holiday = detail["weekendOrHolidayFlg"]
    if detail.get("isAfterDeadline"):
        event.remaining = 0
    return event


def is_open_practice(item: dict) -> bool:
    """一覧の段階で、通常のテニスイベントかつ募集中のものだけ残す。"""
    return (
        item.get("eventType") == "NORMAL"
        and not item.get("pickleballFlg")
        and not item.get("isFull")
        and not item.get("callOff")
        and item.get("wanted", True)
    )


def list_items(state: dict) -> list[dict]:
    """ページ内のイベント一覧の項目を集める。

    都道府県一覧と会場一覧でストアの場所が違うため、一覧項目の形
    （id・eventTitle・startDatetimeString を持つ）で探す。
    """
    found: dict[object, dict] = {}

    def walk(o):
        if isinstance(o, dict):
            if "eventTitle" in o and "startDatetimeString" in o and "id" in o:
                found.setdefault(o["id"], o)
                return
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(state.get("state", state))
    return list(found.values())


def detail_of(state: dict) -> dict:
    return state["state"]["feature"]["event"]["eventDetail"]["EventDetail"]["event"]


def _page_items(client: Client, path: str) -> list[dict]:
    try:
        return list_items(nuxt_state(client.get(path)))
    except Exception as e:  # 1ページの失敗で全体を止めない
        print(f"取得に失敗: {path}: {e}", file=sys.stderr)
        return []


def fetch_events(
    prefs: Preferences,
    now: datetime,
    client: Client | None = None,
    known_places: list[str] | None = None,
) -> tuple[list[Event], list[str]]:
    """イベントと、今回までに見つかった会場コード（新しい順）を返す。"""
    client = client or Client()
    items: dict[str, dict] = {}
    seen_places: list[str] = []

    for name in prefs.prefectures:
        code = PREFECTURE_CODES.get(name)
        if not code:
            print(f"未対応の都道府県名: {name}", file=sys.stderr)
            continue
        page = _page_items(client, f"/event/prefecture/{code}")
        print(f"{name}: 一覧 {len(page)}件", file=sys.stderr)
        for item in page:
            items.setdefault(str(item["id"]), item)
            place = item.get("place") or {}
            prefecture = ((place.get("area") or {}).get("prefecture") or {}).get("name")
            if place.get("code") and prefecture in prefs.prefectures:
                seen_places.append(str(place["code"]))

    places = list(dict.fromkeys(prefs.places + seen_places + (known_places or [])))
    for code in places[: prefs.max_places]:
        page = _page_items(client, f"/place/{code}/events")
        print(f"会場 {code}: {len(page)}件", file=sys.stderr)
        for item in page:
            items.setdefault(str(item["id"]), item)

    candidates = []
    for item in items.values():
        if not is_open_practice(item) or not item.get("startDatetimeString"):
            continue
        event = event_from_list_item(item)
        if passes_list_filters(event, prefs, now):
            candidates.append(event)

    # 詳細ページは上限件数まで。名前がラリー・練習系、レベルが近い、開始が早い順に開く
    candidates.sort(key=lambda e: (not title_hits(e, prefs), level_distance(e, prefs), e.start))
    events: list[Event] = []
    for event in candidates[: prefs.max_details]:
        try:
            detail = detail_of(nuxt_state(client.get(f"/event/{event.id}/info")))
        except Exception as e:  # 1件の失敗で全体を止めない
            print(f"詳細の取得に失敗: {event.url}: {e}", file=sys.stderr)
            continue
        events.append(apply_detail(event, detail))
    print(f"一覧 {len(items)}件 / 候補 {len(candidates)}件 / 詳細取得 {len(events)}件", file=sys.stderr)
    places_out = list(dict.fromkeys(seen_places + (known_places or [])))
    return events, places_out
