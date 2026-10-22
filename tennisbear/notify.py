"""毎朝の更新完了を LINE（Messaging API）に知らせる。

必要な環境変数（GitHub の Secrets に登録）:
  LINE_CHANNEL_ACCESS_TOKEN  チャネルアクセストークン（長期）
  LINE_USER_ID               通知先の自分のユーザーID
どちらかが未設定なら何もせず終了する。
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime

from .render import to_view
from .scoring import Recommendation

PUSH_URL = "https://api.line.me/v2/bot/message/push"
TOP = 3


def build_message(recs: list[Recommendation], page_url: str, now: datetime) -> str:
    exact = sum(r.exact for r in recs)
    near = len(recs) - exact
    lines = [f"🎾 {now:%m/%d} のおすすめを更新しました", f"一致{exact}件＋近い候補{near}件"]
    for i, r in enumerate(recs[:TOP], 1):
        v = to_view(r)
        lines += ["", f"{i}. {v['when']}", v["title"], v["where"]]
    lines += ["", f"一覧: {page_url}"]
    return "\n".join(lines)


def push(token: str, user_id: str, text: str) -> None:
    body = json.dumps(
        {"to": user_id, "messages": [{"type": "text", "text": text[:4900]}]},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        PUSH_URL,
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        urllib.request.urlopen(req, timeout=30).read()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"LINE送信に失敗しました: {e.code} {e.read().decode('utf-8', 'replace')}")


def notify(recs: list[Recommendation], page_url: str, now: datetime) -> bool:
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "")
    user_id = os.environ.get("LINE_USER_ID", "")
    if not token or not user_id:
        print("LINEの設定がないため通知をスキップしました")
        return False
    push(token, user_id, build_message(recs, page_url, now))
    print("LINEに通知しました")
    return True
