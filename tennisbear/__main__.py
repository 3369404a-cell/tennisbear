"""使い方:

  # テニスベアから取得 → data/events.json に保存
  python -m tennisbear fetch   # node が必要

  # おすすめを docs/index.html に書き出す
  python -m tennisbear build --events data/events.json

  # その場の条件で提案をターミナルに出す（設定ファイルは変更しない）
  python -m tennisbear suggest --events data/events.json --keyword ラリー --pref 神奈川県
"""

from __future__ import annotations

import argparse
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .fetch import fetch_events
from .models import load_events, save_events
from .preferences import DEFAULT_PATH, load_preferences
from .render import render_page, to_view, write_page
from .scoring import recommend

JST = ZoneInfo("Asia/Tokyo")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="tennisbear")
    parser.add_argument("--config", type=Path, default=DEFAULT_PATH)
    sub = parser.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch")
    f.add_argument("--out", type=Path, default=Path("data/events.json"))

    b = sub.add_parser("build")
    b.add_argument("--events", type=Path, default=Path("data/events.json"))
    b.add_argument("--out", type=Path, default=Path("docs/index.html"))

    s = sub.add_parser("suggest")
    s.add_argument("--events", type=Path, default=Path("data/events.json"))
    s.add_argument("--keyword", action="append", default=[], help="優先キーワードを追加")
    s.add_argument("--pref", action="append", default=[], help="都道府県をこれに絞る")
    s.add_argument("--level", type=int, action="append", default=[], help="ベアレベルを上書き")
    s.add_argument("--top", type=int, default=10)

    args = parser.parse_args(argv)
    prefs = load_preferences(args.config)
    # 取得データは日本時間・タイムゾーンなしで扱う
    now = datetime.now(JST).replace(tzinfo=None)

    if args.cmd == "fetch":
        events = fetch_events(prefs)
        save_events(events, args.out)
        print(f"{len(events)}件を {args.out} に保存しました")
    elif args.cmd == "build":
        recs = recommend(load_events(args.events), prefs, now)
        write_page(render_page(recs, prefs, now), args.out)
        print(f"{len(recs)}件を {args.out} に書き出しました")
    elif args.cmd == "suggest":
        prefs = replace(
            prefs,
            prefer_keywords=prefs.prefer_keywords + args.keyword,
            prefectures=args.pref or prefs.prefectures,
            levels=args.level or prefs.levels,
            top_n=args.top,
        )
        for r in recommend(load_events(args.events), prefs, now):
            v = to_view(r)
            print(f"[{r.score:>3}] {v['when']}  {v['title']}")
            print(f"      {v['where']}  {' / '.join(v['reasons'])}")
            print(f"      {v['url']}")


if __name__ == "__main__":
    main()
