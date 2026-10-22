# tennisbear

テニスベアの公開イベントから、自分の条件に合うものを毎日まとめてスマホで見られるページを作ります。
各イベントの「テニスベアで申し込む」ボタンからテニスベアの詳細ページに移動し、そこで申し込みます（自動申込はしません）。

## 条件を変える

`config/preferences.toml` を編集します（ベアレベル・エリア・優先キーワード・年代・曜日・時間帯・参加費など）。
ページ上でも都道府県の切り替えとキーワード絞り込みができます。
条件に完全一致しなくても、希望レベルから1段階ずれたもの・練習系の記載がないもの・年代が違うものは「近い候補」として下に並びます（`[near_match]` で調整、ページの「近い候補も表示」で表示切り替え）。

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
- 一覧ページに載るのは開始が近い順の40件だけなので、取れるのは「近いうちに始まるイベント」に限られます。

## 毎日の更新

`.github/workflows/daily.yml` が毎朝 6:45（日本時間）に始まり、7時ごろまでに取得 → 生成 → GitHub Pages へ公開します（GitHub の混雑で数分〜十数分遅れることがあります）。
動かすには、このワークフローがデフォルトブランチ（main）にあることと、リポジトリの Settings → Pages で Source を「GitHub Actions」にすることが必要です。
Actions タブの「Run workflow」から手動でも実行できます。
