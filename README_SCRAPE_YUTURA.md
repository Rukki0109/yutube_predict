# yutura.net スクレイピング実行手順

このドキュメントは、`scripts/scrape_yutura_pages_selenium.py` を使って yutura.net のニュース一覧ページをレンダリングし、記事一覧を CSV にまとめる手順をまとめたものです。

前提
- Windows（PowerShell）環境
- Python 3.x がインストール済み
- 必要な Python パッケージは `requirements-scrape.txt` に記載

推奨: Anaconda の仮想環境（例: `faceenv`）を使うと依存管理が簡単です。

セットアップ
1. （任意）Anaconda 環境をアクティブにする
   ```powershell
   conda activate faceenv
   ```
2. 必要パッケージをインストール
   ```powershell
   python -m pip install -r requirements-scrape.txt
   ```

実行方法（例: ページ 1..5 を取得して HTML を保存する）
```powershell
# リポジトリのルートで実行
.\scripts\run_scrape_yutura.ps1 -Start 1 -End 5 -Out "data\yutura_news_pages_1-5.csv" -SaveHtmlDir "data\yutura_pages_html" -Headless
```

直接 Python を使う場合の例:
```powershell
python scripts\scrape_yutura_pages_selenium.py --start 1 --end 5 --out data\yutura_news_pages_1-5.csv --headless --save-html-dir data\yutura_pages_html
```

出力
- 統合 CSV: `data/yutura_news_pages_{start}-{end}.csv`（rank,page,title,url,date,source_page）
- オプション: ページごとのレンダリング HTML を保存するディレクトリ

注意点
- yutura は直接のリクエストをブロックする場合があります（403）。そのためスクリプトは Selenium でレンダリングする方式を採用しています。
- WebDriver は `webdriver-manager` により自動でダウンロードされます。初回はダウンロードに時間がかかる場合があります。
- ブラウザプロセスのログやエラーはターミナルに出力されます。ヘッドレス実行時でも一時的にプロセスが起動します。

トラブルシューティング
- ChromeDriver が動かない／権限エラー: 一時的に `--headless` を外して GUI 実行して動作を確認してください。
- ページの構造が変わるとパーサが失敗することがあります。`data/yutura_pages_html` に保存された HTML を手動で確認し、`scripts/scrape_yutura_pages_selenium.py` の `parse_page_html` を調整してください。

---
作業を自動化したい場合は、Windows タスクスケジューラや cron（WSL）等でこの PowerShell スクリプトを定期的に実行できます。
