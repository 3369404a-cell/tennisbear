import json
import unittest
from datetime import datetime

from tennisbear.fetch import (
    PREFECTURE_CODES,
    apply_detail,
    event_from_list_item,
    fetch_events,
    is_open_practice,
    nuxt_state,
)
from tennisbear.preferences import DEFAULT_PATH, load_preferences

# テニスベアの一覧・詳細ページの __NUXT__ に入っている形（必要な項目だけ抜粋）
LIST_ITEM = {
    "id": 1687562,
    "eventType": "NORMAL",
    "eventTitle": "大和で基礎練！",
    "startDatetimeString": "2026-10-23T06:00:00.000+09:00",
    "place": {
        "name": "KPI LINK 神奈川県大和市テニスコート",
        "address": "〒242-0029 神奈川県大和市上草柳６丁目９−２３",
        "area": {"prefecture": {"code": "pref14", "name": "神奈川県"}},
    },
    "minLevel": {"id": 5, "name": "中級"},
    "maxLevel": {"id": 8, "name": "超上級"},
    "isFull": False,
    "callOff": False,
    "wanted": True,
    "pickleballFlg": False,
}
DETAIL = {
    "id": 1687562,
    "endDateTime": "2026-10-23T08:00:00.000+09:00",
    "eventContents": "一通りの基礎練習を行います。\n・クロスラリー 10分",
    "organizer": {"age": {"name": "30代"}},
    "priceOverview": 1000,
    "maxParticipantsNumber": 4,
    "nowParticipantsNumber": 2,
    "isAfterDeadline": False,
    "eventTagList": [{"id": 9, "name": "練習多め"}, {"id": 1, "name": "シングルス"}],
    "participantInfo": {
        "aboutAgeInfo": {"aboutAgeTwentyCount": 1, "aboutAgeThirtyCount": 2, "aboutAgeFortyCount": 0}
    },
}


def page(state: dict) -> str:
    # 本物と同じく「値を引数で渡す即時関数」の形で埋め込む
    return f"<html><script>window.__NUXT__=(function(a){{return {json.dumps(state)}}}(null));</script></html>"


def list_state(items):
    return {"state": {"feature": {"event": {"eventSearch": {"EventList": {"eventList": items}}}}}}


def detail_state(detail):
    return {"state": {"feature": {"event": {"eventDetail": {"EventDetail": {"event": detail}}}}}}


class FakeClient:
    def __init__(self, pages):
        self.pages = pages
        self.requested = []

    def get(self, path):
        self.requested.append(path)
        return self.pages[path]


class FetchTest(unittest.TestCase):
    def test_prefecture_codes(self):
        self.assertEqual(PREFECTURE_CODES["東京都"], "pref13")
        self.assertEqual(PREFECTURE_CODES["神奈川県"], "pref14")
        self.assertEqual(PREFECTURE_CODES["埼玉県"], "pref11")

    def test_nuxt_state(self):
        self.assertEqual(nuxt_state(page({"x": [1, "あ"]})), {"x": [1, "あ"]})

    def test_normalize(self):
        e = apply_detail(event_from_list_item(LIST_ITEM), DETAIL)
        self.assertEqual(e.url, "https://www.tennisbear.net/event/1687562/info")
        self.assertEqual(e.start, datetime(2026, 10, 23, 6, 0))
        self.assertEqual(e.end, datetime(2026, 10, 23, 8, 0))
        self.assertEqual((e.prefecture, e.city), ("神奈川県", "大和市"))
        self.assertEqual((e.level_min, e.level_max), (5, 8))
        self.assertEqual((e.fee, e.capacity, e.remaining), (1000, 4, 2))
        self.assertEqual(e.organizer_age_decade, 30)
        self.assertEqual(sorted(e.participant_age_decades), [20, 30, 30])
        self.assertEqual(e.tags, ["練習多め", "シングルス"])

    def test_skips_full_pickleball_and_tournaments(self):
        self.assertTrue(is_open_practice(LIST_ITEM))
        self.assertFalse(is_open_practice({**LIST_ITEM, "isFull": True}))
        self.assertFalse(is_open_practice({**LIST_ITEM, "pickleballFlg": True}))
        self.assertFalse(is_open_practice({**LIST_ITEM, "eventType": "TOURNAMENT"}))

    def test_fetch_opens_details_only_for_matching_events(self):
        low = {**LIST_ITEM, "id": 2, "minLevel": {"id": 1}, "maxLevel": {"id": 3}}
        client = FakeClient({
            "/event/prefecture/pref14": page(list_state([LIST_ITEM, low])),
            "/event/1687562/info": page(detail_state(DETAIL)),
        })
        prefs = load_preferences(DEFAULT_PATH)
        prefs.prefectures = ["神奈川県"]
        events = fetch_events(prefs, client)
        self.assertEqual([e.id for e in events], ["1687562"])
        self.assertNotIn("/event/2/info", client.requested)


if __name__ == "__main__":
    unittest.main()
