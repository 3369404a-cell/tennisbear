"""テニスベアの公開ページからイベントを取得して Event に正規化する。

- robots.txt で /api/ が禁止されているため、公開 HTML ページだけを読む。
- robots.txt の Crawl-delay: 10 に合わせ、リクエスト間隔を10秒空ける。
- 一覧ページ（都道府県別）には開始が近い順に40件だけ載っている。
  一覧で必須条件に合うものだけ詳細ページを開き、年代・料金・本文を取る。
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
from .scoring import passes_list_filters

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
        level_min=(item.get("minLevel") or {}).get("id"),
        level_max=(item.get("maxLevel") or {}).get("id"),
    )


def apply_detail(event: Event, detail: dict) -> Event:
    event.end = _dt(detail.get("endDateTime"))
    event.description = detail.get("eventContents") or ""
    event.tags = [t["name"] for t in detail.get("eventTagList") or []]
    event.fee = detail.get("priceOverview")
    event.capacity = detail.get("maxParticipantsNumber")
    if event.capacity is not None and detail.get("nowParticipantsNumber") is not None:
        event.remaining = event.capacity - detail["nowParticipantsNumber"]
    event.organizer_age_decade = _decade(((detail.get("organizer") or {}).get("age") or {}).get("name"))
    ages = ((detail.get("participantInfo") or {}).get("aboutAgeInfo")) or {}
    event.participant_age_decades = [
        decade for key, decade in AGE_COUNT_KEYS.items() for _ in range(ages.get(key) or 0)
    ]
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
    return state["state"]["feature"]["event"]["eventSearch"]["EventList"]["eventList"]


def detail_of(state: dict) -> dict:
    return state["state"]["feature"]["event"]["eventDetail"]["EventDetail"]["event"]


def fetch_events(prefs: Preferences, client: Client | None = None) -> list[Event]:
    client = client or Client()
    events: list[Event] = []
    for name in prefs.prefectures:
        code = PREFECTURE_CODES.get(name)
        if not code:
            print(f"未対応の都道府県名: {name}", file=sys.stderr)
            continue
        items = list_items(nuxt_state(client.get(f"/event/prefecture/{code}")))
        print(f"{name}: 一覧 {len(items)}件", file=sys.stderr)
        for item in items:
            if not is_open_practice(item):
                continue
            event = event_from_list_item(item)
            if not passes_list_filters(event, prefs):
                continue
            try:
                detail = detail_of(nuxt_state(client.get(f"/event/{event.id}/info")))
            except Exception as e:  # 1件の失敗で全体を止めない
                print(f"詳細の取得に失敗: {event.url}: {e}", file=sys.stderr)
                continue
            events.append(apply_detail(event, detail))
    return events
