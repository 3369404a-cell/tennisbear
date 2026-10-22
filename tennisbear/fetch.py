"""テニスベアからイベントを取得して Event に正規化する。

TODO: テニスベアのページ構成を確認できたら実装する。
開発環境から tennisbear.net への通信がまだ許可されておらず、
実際のページを見ないと取得・解析処理を正しく書けないため未実装。
"""

from __future__ import annotations

from .models import Event


class FetchNotImplemented(RuntimeError):
    pass


def fetch_events(prefectures: list[str]) -> list[Event]:
    raise FetchNotImplemented(
        "テニスベアの取得処理は未実装です。"
        "data/events.json を用意して `python -m tennisbear build --events data/events.json` で生成できます。"
    )
