import unittest
from datetime import datetime, timedelta

from tennisbear.models import Event
from tennisbear.preferences import DEFAULT_PATH, load_preferences
from tennisbear.render import render_page
from tennisbear.scoring import is_candidate, recommend

NOW = datetime(2026, 10, 22, 9, 0)


def ev(**kw) -> Event:
    base = dict(
        id="1",
        title="ラリー練習会",
        url="https://example.invalid/e/1",
        start=NOW + timedelta(days=2),
        prefecture="東京都",
        level_min=4,
        level_max=6,
    )
    base.update(kw)
    return Event(**base)


class ScoringTest(unittest.TestCase):
    def setUp(self):
        self.prefs = load_preferences(DEFAULT_PATH)

    def test_filters_out_other_prefecture(self):
        self.assertFalse(is_candidate(ev(prefecture="千葉県"), self.prefs, NOW))

    def test_filters_out_level_outside_5_6(self):
        self.assertFalse(is_candidate(ev(level_min=1, level_max=3), self.prefs, NOW))
        self.assertTrue(is_candidate(ev(level_min=6, level_max=8), self.prefs, NOW))

    def test_filters_out_full_and_past(self):
        self.assertFalse(is_candidate(ev(remaining=0), self.prefs, NOW))
        self.assertFalse(is_candidate(ev(start=NOW - timedelta(hours=1)), self.prefs, NOW))

    def test_practice_and_age_ranks_above_tournament(self):
        practice = ev(id="a", title="ラリー・球出し練習", organizer_age_decade=30,
                      participant_age_decades=[20, 30, 30])
        tournament = ev(id="b", title="大会形式ゲーム会", organizer_age_decade=50)
        recs = recommend([tournament, practice], self.prefs, NOW)
        self.assertEqual([r.event.id for r in recs], ["a", "b"])
        self.assertIn("主催30代", recs[0].reasons)

    def test_render_escapes_script_tags(self):
        recs = recommend([ev(title="</script><b>x")], self.prefs, NOW)
        html = render_page(recs, self.prefs, NOW)
        self.assertNotIn("</script><b>", html)
        self.assertIn("テニスベアで申し込む", html)


if __name__ == "__main__":
    unittest.main()
