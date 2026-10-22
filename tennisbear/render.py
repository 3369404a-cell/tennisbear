from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

from .analysis import analyze
from .calendar_jp import holidays, week_window
from .preferences import Preferences
from .scoring import TITLE, Recommendation

WEEKDAYS = "月火水木金土日"

TEMPLATE = """<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>土日祝テニス練習会</title>
<style>
:root {
  --bg: #f6f7f4; --card: #ffffff; --text: #1d2420; --muted: #66706a;
  --accent: #2f7d4f; --accent-text: #ffffff; --chip: #e6efe9; --line: #dde3df;
  --panel: #f1f4f1;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #121614; --card: #1b211e; --text: #e8ece9; --muted: #9aa59f;
    --accent: #5fbf85; --accent-text: #0d1310; --chip: #24302a; --line: #2c3631;
    --panel: #161b18;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Hiragino Sans", "Noto Sans JP", sans-serif; }
main { max-width: 720px; margin: 0 auto; padding: 16px; }
h1 { font-size: 1.3rem; margin: 8px 0 4px; }
.meta { color: var(--muted); font-size: .85rem; margin-bottom: 12px; line-height: 1.5; }
.filters { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 10px; }
.filters button { border: 1px solid var(--line); background: var(--card); color: var(--text);
  border-radius: 999px; padding: 6px 12px; font-size: .85rem; }
.filters button[aria-pressed="true"] { background: var(--accent); color: var(--accent-text); border-color: var(--accent); }
input[type=search] { width: 100%; padding: 10px 12px; border-radius: 10px; border: 1px solid var(--line);
  background: var(--card); color: var(--text); font-size: 1rem; margin-bottom: 12px; }
.section { font-size: 1rem; margin: 20px 0 4px; }
.section-note { color: var(--muted); font-size: .8rem; margin: 0 0 10px; }
.card { background: var(--card); border: 1px solid var(--line); border-radius: 14px; padding: 14px; margin-bottom: 12px; }
.card h2 { font-size: 1rem; margin: 0 0 6px; line-height: 1.4; }
.when { font-weight: 600; }
.where, .info { color: var(--muted); font-size: .88rem; margin-top: 2px; }
.tags { display: flex; flex-wrap: wrap; gap: 6px; margin: 8px 0; }
.tags span { background: var(--chip); border-radius: 6px; padding: 2px 8px; font-size: .78rem; }
.tags span.miss { background: transparent; border: 1px dashed var(--line); color: var(--muted); }
.people { background: var(--panel); border-radius: 10px; padding: 8px 10px; margin: 6px 0 10px; font-size: .82rem; line-height: 1.6; }
.people b { font-weight: 600; }
.people .comment { margin-top: 2px; }
.apply { display: block; text-align: center; background: var(--accent); color: var(--accent-text);
  text-decoration: none; font-weight: 600; padding: 10px; border-radius: 10px; }
.empty { color: var(--muted); text-align: center; padding: 20px 0; font-size: .9rem; }
</style>
</head>
<body>
<main>
  <h1>🎾 土日祝のテニス練習会</h1>
  <div class="meta">__META__</div>
  <div class="filters" id="days"></div>
  <div class="filters" id="prefs"></div>
  <input type="search" id="q" placeholder="キーワードで絞り込み（例: 球出し, 川崎, 30代）">
  <div id="list"></div>
</main>
<script>
const EVENTS = __DATA__;
const list = document.getElementById("list");
const q = document.getElementById("q");
function el(tag, cls, text) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text != null) n.textContent = text;
  return n;
}
function chips(box, values, onChange) {
  const active = new Set();
  const all = el("button", null, "すべて");
  const buttons = [all];
  all.setAttribute("aria-pressed", "true");
  all.onclick = () => { active.clear(); sync(); };
  box.appendChild(all);
  values.forEach(v => {
    const b = el("button", null, v);
    b.dataset.v = v;
    b.setAttribute("aria-pressed", "false");
    b.onclick = () => { active.has(v) ? active.delete(v) : active.add(v); sync(); };
    buttons.push(b);
    box.appendChild(b);
  });
  function sync() {
    all.setAttribute("aria-pressed", String(!active.size));
    buttons.slice(1).forEach(b => b.setAttribute("aria-pressed", String(active.has(b.dataset.v))));
    onChange();
  }
  return v => !active.size || active.has(v);
}
const dayOk = chips(document.getElementById("days"), [...new Set(EVENTS.map(e => e.day))], draw);
const prefOk = chips(document.getElementById("prefs"), [...new Set(EVENTS.map(e => e.prefecture).filter(Boolean))], draw);
function draw() {
  const words = q.value.trim().split(/\\s+/).filter(Boolean);
  const shown = EVENTS.filter(e => dayOk(e.day) && prefOk(e.prefecture) &&
    words.every(w => e.haystack.includes(w)));
  list.replaceChildren();
  section("イベント名がラリー・練習系", "名前に「ラリー」「練習」などが入っているもの（日付順）",
    shown.filter(e => e.titled));
  section("その他のおすすめ", "名前には入っていないが、内容・レベル・年代が合いそうなもの（おすすめ順）",
    shown.filter(e => !e.titled));
}
function section(title, note, items) {
  list.appendChild(el("h3", "section", `${title}（${items.length}件）`));
  list.appendChild(el("p", "section-note", note));
  if (!items.length) { list.appendChild(el("p", "empty", "該当するイベントはありません")); return; }
  items.forEach(card);
}
function card(e) {
  const c = el("article", "card");
  c.appendChild(el("h2", null, e.title));
  c.appendChild(el("div", "when", e.when));
  c.appendChild(el("div", "where", e.where));
  if (e.info) c.appendChild(el("div", "info", e.info));
  const tags = el("div", "tags");
  e.reasons.forEach(r => tags.appendChild(el("span", null, r)));
  e.misses.forEach(m => tags.appendChild(el("span", "miss", m)));
  c.appendChild(tags);
  if (e.people.length || e.comment) {
    const p = el("div", "people");
    const head = el("div");
    head.appendChild(el("b", null, "参加者分析"));
    p.appendChild(head);
    e.people.forEach(line => p.appendChild(el("div", null, line)));
    if (e.comment) p.appendChild(el("div", "comment", "→ " + e.comment));
    c.appendChild(p);
  }
  const a = el("a", "apply", "テニスベアで申し込む");
  a.href = e.url; a.target = "_blank"; a.rel = "noopener";
  c.appendChild(a);
  list.appendChild(c);
}
q.addEventListener("input", draw);
draw();
</script>
</body>
</html>
"""


def _day(d: datetime) -> str:
    label = f"{d.month}/{d.day}（{WEEKDAYS[d.weekday()]}"
    if d.date() in holidays(d.year):
        label += "・祝"
    return label + "）"


def _when(r: Recommendation) -> str:
    s = r.event.start
    text = f"{_day(s)}{s:%H:%M}"
    if r.event.end:
        text += f"〜{r.event.end:%H:%M}"
    return text


def _info(r: Recommendation) -> str:
    e = r.event
    parts = []
    if e.fee is not None:
        parts.append(f"¥{e.fee:,}")
    if e.capacity is not None:
        parts.append(f"定員{e.capacity}名")
    if e.organizer_age_decade:
        parts.append(f"主催者{e.organizer_age_decade}代")
    return " ・ ".join(parts)


def to_view(r: Recommendation, prefs: Preferences) -> dict:
    e = r.event
    where = " ".join(x for x in (e.prefecture, e.city, e.venue) if x)
    when = _when(r)
    people = analyze(e, prefs)
    return {
        "title": e.title,
        "url": e.url,
        "prefecture": e.prefecture,
        "day": _day(e.start),
        "when": when,
        "where": where,
        "info": _info(r),
        "reasons": r.reasons,
        "misses": r.misses,
        "titled": r.category == TITLE,
        "people": people.lines,
        "comment": people.comment,
        "haystack": "\n".join(
            [e.title, " ".join(e.tags), e.description, where, when, *people.lines, people.comment]
        ),
    }


def render_page(recs: list[Recommendation], prefs: Preferences, generated_at: datetime) -> str:
    data = json.dumps([to_view(r, prefs) for r in recs], ensure_ascii=False)
    # </script> などで埋め込みが途切れないようにする
    data = data.replace("<", "\\u003c")
    start, end = week_window(generated_at, prefs.weeks_from, prefs.weeks)
    last = datetime.fromordinal(end.date().toordinal() - 1)
    levels = "・".join(str(lv) for lv in prefs.levels) or "指定なし"
    titled = sum(r.category == TITLE for r in recs)
    meta = (
        f"{generated_at:%Y/%m/%d %H:%M} 更新 ・ "
        f"対象 {start.month}/{start.day}〜{last.month}/{last.day} の"
        f"{'土日祝' if prefs.weekend_holiday_only else '全日'} ・ "
        f"ベアレベル{levels} ・ {'/'.join(prefs.prefectures) or '全エリア'} ・ "
        f"ラリー・練習系{titled}件＋その他のおすすめ{len(recs) - titled}件"
    )
    return TEMPLATE.replace("__META__", html.escape(meta)).replace("__DATA__", data)


def write_page(html: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
