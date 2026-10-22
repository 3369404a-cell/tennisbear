import unittest
from datetime import datetime

from tennisbear.models import Event
from tennisbear.notify import build_message
from tennisbear.scoring import Recommendation


class BuildMessageTest(unittest.TestCase):
    def test_message_has_counts_top_events_and_url(self):
        e = Event(id="1", title="ラリー練習", url="https://example.com/1",
                  start=datetime(2026, 10, 25, 10, 0), prefecture="東京都", city="世田谷区")
        recs = [Recommendation(event=e, score=10), Recommendation(event=e, score=5, misses=["年代"])]
        text = build_message(recs, "https://example.com/page", datetime(2026, 10, 24, 7, 0))
        self.assertIn("一致1件＋近い候補1件", text)
        self.assertIn("ラリー練習", text)
        self.assertIn("https://example.com/page", text)


if __name__ == "__main__":
    unittest.main()
