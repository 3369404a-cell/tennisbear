# tennisbear

テニスベアの公開イベントから、自分の条件に合うものを毎日まとめてスマホで見られるページを作ります。
各イベントの「テニスベアで申し込む」ボタンからテニスベアの詳細ページに移動し、そこで申し込みます（自動申込はしません）。

## ページの中身

- 対象は**来週と再来週の土日祝**のイベント（`[schedule]` の `weeks_from` / `weeks` / `weekend_holiday_only` で変更可）。
- **イベント名がラリー・練習系**：名前に「ラリー」「練習」などが入っているものを日付順に全部（キーワードは `title_keywords`）。
- **その他のおすすめ**：名前には入っていないが、タグ（練習多め）・本文・レベル・主催者や参加者の年代から合いそうなものをおすすめ順に（基準は `[recommend]` の `other_min_score`）。
- 各イベントに**参加者分析**（参加人数・男女・年代の内訳と希望年代の割合・レベルの内訳と平均・ひとことまとめ）を表示。
- 希望レベルから1段階ずれたものも載せ、外れている条件は点線のタグで表示。
- ページ上で日付・都道府県・キーワードで絞り込めます。

## 条件を変える

`config/preferences.toml` を編集します（ベアレベル・エリア・キーワード・年代・期間・時間帯・参加費・巡回する会場など）。

## コマンド

```sh
python -m tennisbear fetch                          # テニスベアから取得 → data/events.json
python -m tennisbear build                          # おすすめページを docs/index.html に生成
python -m tennisbear suggest --keyword 球出し --pref 神奈川県   # その場の条件で提案を表示
python -m unittest discover -s tests -t .           # テスト
```

Python 3.11 以上と Node.js が必要です（外部ライブラリは不要）。

## 取得のしかた

- 公開ページ（都道府県別の一覧 `/event/prefecture/prefNN` と詳細 `/event/{id}/info`）だけを読みます。robots.txt で禁止されている `/api/` は使いません。
- robots.txt の `Crawl-delay: 10` に合わせ、リクエストは10秒間隔です。
- ページ内の `window.__NUXT__` に入っている構造化データを Node の vm で取り出しています。
- 都道府県別の一覧は開始が近い順の40件しか載らないため、会場ごとの一覧（`/place/{コード}/events`）も巡回します。巡回する会場は設定の `places` と、都道府県一覧で見つかった会場です（見つかった会場は `data/places.json` に記録し、次回以降も巡回）。

## 毎日の更新

`.github/workflows/daily.yml` が毎朝 6:25（日本時間）に始まり、7時ごろまでに取得 → 生成 → GitHub Pages へ公開します（GitHub の混雑で数分〜十数分遅れることがあります）。
動かすには、このワークフローがデフォルトブランチ（main）にあることと、リポジトリの Settings → Pages で Source を「GitHub Actions」にすることが必要です。
Actions タブの「Run workflow」から手動でも実行できます。
