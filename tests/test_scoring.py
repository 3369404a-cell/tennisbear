import unittest
from datetime import datetime

from tennisbear.analysis import analyze
from tennisbear.calendar_jp import holidays, week_window
from tennisbear.models import Event
from tennisbear.preferences import DEFAULT_PATH, load_preferences
from tennisbear.render import render_page
from tennisbear.scoring import OTHER, TITLE, is_candidate, recommend

NOW = datetime(2026, 10, 22, 7, 0)  # 木曜。来週 = 10/26〜11/1、再来週 = 11/2〜11/8
SAT_NEXT_WEEK = datetime(2026, 10, 31, 10, 0)


def ev(**kw) -> Event:
    base = dict(
        id="1",
        title="ラリー練習会",
        url="https://example.invalid/e/1",
        start=SAT_NEXT_WEEK,
        prefecture="東京都",
        level_min=4,
        level_max=6,
    )
    base.update(kw)
    return Event(**base)


class CalendarTest(unittest.TestCase):
    def test_holidays(self):
        h = holidays(2026)
        self.assertIn(datetime(2026, 11, 3).date(), h)  # 文化の日
        self.assertIn(datetime(2026, 5, 6).date(), h)  # 振替休日
        self.assertIn(datetime(2026, 9, 22).date(), h)  # 国民の休日

    def test_next_two_weeks(self):
        self.assertEqual(week_window(NOW, 1, 2), (datetime(2026, 10, 26), datetime(2026, 11, 9)))


class ScoringTest(unittest.TestCase):
    def setUp(self):
        self.prefs = load_preferences(DEFAULT_PATH)

    def test_only_weekends_and_holidays_in_next_two_weeks(self):
        ok = lambda d: is_candidate(ev(start=d), self.prefs, NOW)  # noqa: E731
        self.assertFalse(ok(datetime(2026, 10, 24, 10)))  # 今週の土曜
        self.assertFalse(ok(datetime(2026, 10, 28, 10)))  # 来週の水曜
        self.assertTrue(ok(datetime(2026, 10, 31, 10)))  # 来週の土曜
        self.assertTrue(ok(datetime(2026, 11, 3, 10)))  # 文化の日（火）
        self.assertTrue(ok(datetime(2026, 11, 8, 10)))  # 再来週の日曜
        self.assertFalse(ok(datetime(2026, 11, 14, 10)))  # 3週間後

    def test_site_holiday_flag_is_respected(self):
        self.assertTrue(is_candidate(ev(start=datetime(2026, 10, 28, 10), weekend_or_holiday=True), self.prefs, NOW))

    def test_area_level_and_full(self):
        self.assertFalse(is_candidate(ev(prefecture="千葉県"), self.prefs, NOW))
        self.assertFalse(is_candidate(ev(level_min=1, level_max=3), self.prefs, NOW))
        self.assertTrue(is_candidate(ev(level_min=7, level_max=9), self.prefs, NOW))  # 1段階ずれは残す
        self.assertFalse(is_candidate(ev(remaining=0), self.prefs, NOW))

    def test_title_keyword_events_and_other_recommendations(self):
        titled = ev(id="t", title="【大田区】ラリー中心の会")
        good_other = ev(id="o", title="ダブルス会", tags=["練習多め"],
                        description="前半は球出しと基礎", organizer_age_decade=30,
                        participant_age_decades=[20, 30])
        weak_other = ev(id="w", title="ゲーム会", organizer_age_decade=50)
        recs = recommend([weak_other, good_other, titled], self.prefs, NOW)
        self.assertEqual([(r.event.id, r.category) for r in recs], [("t", TITLE), ("o", OTHER)])
        self.assertIn("名前に「ラリー」", recs[0].reasons)

    def test_title_events_are_listed_by_date(self):
        later = ev(id="later", start=datetime(2026, 11, 7, 9))
        sooner = ev(id="sooner", start=datetime(2026, 11, 1, 9))
        self.assertEqual([r.event.id for r in recommend([later, sooner], self.prefs, NOW)], ["sooner", "later"])


class AnalysisTest(unittest.TestCase):
    def test_summarizes_participants(self):
        prefs = load_preferences(DEFAULT_PATH)
        a = analyze(ev(participants=4, capacity=6, remaining=2, men=3, women=1,
                       participant_age_decades=[20, 30, 30, 40],
                       participant_levels=[5, 5, 6, 6]), prefs)
        self.assertEqual(a.lines[0], "参加 4/6名（残り2）")
        self.assertIn("男性3・女性1", a.lines)
        self.assertIn("年代: 20代×1 30代×2 40代×1（希望年代 75%）", a.lines)
        self.assertIn("レベル: Lv5×2 Lv6×2（平均5.5）", a.lines)
        self.assertIn("同年代が中心", a.comment)
        self.assertIn("レベルが近い人が多い", a.comment)


class RenderTest(unittest.TestCase):
    def test_render_escapes_script_tags_and_shows_analysis(self):
        prefs = load_preferences(DEFAULT_PATH)
        recs = recommend([ev(title="ラリー</script><b>x", participants=2, capacity=4,
                             participant_levels=[5, 6])], prefs, NOW)
        html = render_page(recs, prefs, NOW)
        self.assertNotIn("</script><b>", html)
        self.assertIn("テニスベアで申し込む", html)
        self.assertIn("Lv5×1 Lv6×1", html)


if __name__ == "__main__":
    unittest.main()
