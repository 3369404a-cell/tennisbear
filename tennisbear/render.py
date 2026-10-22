from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

from .preferences import Preferences
from .scoring import Recommendation

WEEKDAYS = "月火水木金土日"

TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>おすすめテニスイベント</title>
<style>
:root {
  --bg: #f6f7f4; --card: #ffffff; --text: #1d2420; --muted: #66706a;
  --accent: #2f7d4f; --accent-text: #ffffff; --chip: #e6efe9; --line: #dde3df;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #121614; --card: #1b211e; --text: #e8ece9; --muted: #9aa59f;
    --accent: #5fbf85; --accent-text: #0d1310; --chip: #24302a; --line: #2c3631;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Noto Sans JP", sans-serif; }
main { max-width: 720px; margin: 0 auto; padding: 16px; }
h1 { font-size: 1.3rem; margin: 8px 0 4px; }
.meta { color: var(--muted); font-size: .85rem; margin-bottom: 12px; }
.filters { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.filters button { border: 1px solid var(--line); background: var(--card); color: var(--text);
  border-radius: 999px; padding: 6px 12px; font-size: .85rem; }
.filters button[aria-pressed="true"] { background: var(--accent); color: var(--accent-text); border-color: var(--accent); }
input[type=search] { width: 100%; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--line);
  background: var(--card); color: var(--text); font-size: 1rem; margin-bottom: 12px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 14px; margin-bottom: 12px; }
.card h2 { font-size: 1rem; margin: 0 0 6px; line-height: 1.4; }
.when { font-weight: 600; }
.where, .info { color: var(--muted); font-size: .88rem; margin-top: 2px; }
.tags { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0 10px; }
.tags span { background: var(--chip); border-radius: 6px; padding: 2px 8px; font-size: .78rem; }
.apply { display: block; text-align: center; background: var(--accent); color: var(--accent-text);
  text-decoration: none; font-weight: 600; padding: 10px; border-radius: 10px; }
.empty { color: var(--muted); text-align: center; padding: 32px 0; }
</style>
</head>
<body>
<main>
  <h1>🎾 おすすめテニスイベント</h1>
  <div class="meta">__META__</div>
  <div class="filters" id="prefs"></div>
  <input type="search" id="q" placeholder="キーワードで絞り込み（例: ラリー, 川崎, 土曜）">
  <div id="list"></div>
</main>
<script>
const EVENTS = __DATA__;
const list = document.getElementById("list");
const q = document.getElementById("q");
const prefBox = document.getElementById("prefs");
const active = new Set(EVENTS.map(e => e.prefecture).filter(Boolean));
[...active].forEach(p => {
  const b = document.createElement("button");
  b.textContent = p; b.setAttribute("aria-pressed", "true");
  b.onclick = () => {
    active.has(p) ? active.delete(p) : active.add(p);
    b.setAttribute("aria-pressed", String(active.has(p)));
    draw();
  };
  prefBox.appendChild(b);
});
function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}
function draw() {
  const words = q.value.trim().split(/\\s+/).filter(Boolean);
  const shown = EVENTS.filter(e =>
    (!e.prefecture || active.has(e.prefecture)) &&
    words.every(w => e.haystack.includes(w)));
  list.replaceChildren();
  if (!shown.length) { list.appendChild(el("p", "empty", "条件に合うイベントがありません")); return; }
  for (const e of shown) {
    const c = el("article", "card");
    c.appendChild(el("h2", null, e.title));
    c.appendChild(el("div", "when", e.when));
    c.appendChild(el("div", "where", e.where));
    if (e.info) c.appendChild(el("div", "info", e.info));
    const tags = el("div", "tags");
    e.reasons.forEach(r => tags.appendChild(el("span", null, r)));
    c.appendChild(tags);
    const a = el("a", "apply", "テニスベアで申し込む");
    a.href = e.url; a.target = "_blank"; a.rel = "noopener";
    c.appendChild(a);
    list.appendChild(c);
  }
}
q.addEventListener("input", draw);
draw();
</script>
</body>
</html>
"""


def _when(r: Recommendation) -> str:
    s = r.event.start
    text = f"{s.month}/{s.day}（{WEEKDAYS[s.weekday()]}）{s:%H:%M}"
    if r.event.end:
        text += f"〜{r.event.end:%H:%M}"
    return text


def _info(r: Recommendation) -> str:
    e = r.event
    parts = []
    if e.fee is not None:
        parts.append(f"¥{e.fee:,}")
    if e.remaining is not None and e.capacity is not None:
        parts.append(f"残り{e.remaining}/{e.capacity}名")
    return " ・ ".join(parts)


def to_view(r: Recommendation) -> dict:
    e = r.event
    where = " ".join(x for x in (e.prefecture, e.city, e.venue) if x)
    when = _when(r)
    return {
        "title": e.title,
        "url": e.url,
        "prefecture": e.prefecture,
        "when": when,
        "where": where,
        "info": _info(r),
        "reasons": r.reasons,
        "haystack": "\n".join([e.title, " ".join(e.tags), e.description, where, when]),
    }


def render_page(recs: list[Recommendation], prefs: Preferences, generated_at: datetime) -> str:
    data = json.dumps([to_view(r) for r in recs], ensure_ascii=False)
    # </script> などで埋め込みが途切れないようにする
    data = data.replace("<", "\\u003c")
    levels = "・".join(str(lv) for lv in prefs.levels) or "指定なし"
    meta = (
        f"{generated_at:%Y/%m/%d %H:%M} 更新 ・ {len(recs)}件 ・ "
        f"ベアレベル{levels} ・ {'/'.join(prefs.prefectures) or '全エリア'}"
    )
    return TEMPLATE.replace("__META__", html.escape(meta)).replace("__DATA__", data)


def write_page(html: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
