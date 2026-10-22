# tennisbear

テニスベアの公開イベントから、自分の条件に合うものを毎日まとめてスマホで見られるページを作ります。
各イベントの「テニスベアで申し込む」ボタンからテニスベアの詳細ページに移動し、そこで申し込みます（自動申込はしません）。

## 条件を変える

`config/preferences.toml` を編集します（ベアレベル・エリア・優先キーワード・年代・曜日・時間帯・参加費など）。
ページ上でも都道府県の切り替えとキーワード絞り込みができます。

## コマンド

```sh
python -m tennisbear fetch                          # テニスベアから取得 → data/events.json（未実装）
python -m tennisbear build                          # おすすめページを docs/index.html に生成
python -m tennisbear suggest --keyword 球出し --pref 神奈川県   # その場の条件で提案を表示
python -m unittest discover -s tests -t .           # テスト
```

Python 3.11 以上、外部ライブラリ不要。

## 毎日の更新

`.github/workflows/daily.yml` が取得 → 生成 → GitHub Pages へ公開を行います。
取得処理（`tennisbear/fetch.py`）の実装後に schedule を有効にし、リポジトリの Settings → Pages で Source を「GitHub Actions」にしてください。
