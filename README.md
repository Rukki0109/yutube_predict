# YouTube Trend Analysis

このリポジトリは日本のYouTube急上昇データを解析し、外部シグナル（例: yutura.net）を統合して再生予測を行う研究用プロジェクトです。

概要
- トレンドデータ取得: `yt_trend/get_trending.py`
- yutura スクレイピング: `scripts/scrape_yutura_*` 系
- 外部特徴量ビルド: `scripts/build_yutura_features.py`
- 予測実行（Yutura 結合オプション付き）: `scripts/predict_with_optional_yutura.py`

使い方（ローカル）
1. conda 環境をアクティベート（例: `faceenv`）
   ```powershell
   conda activate faceenv
   ```
2. 依存インストール（環境定義を利用）
   ```powershell
   conda env create -f environment.yml -n faceenv_local  # あるいは既存環境へ pip install -r requirements.txt
   ```
3. スクリプト実行例
   ```powershell
   python scripts\build_yutura_features.py --trend trend_data\trending_...csv --yutura data\yutura_news_pages_2025xxxx_1-5.csv --out data\features_yutura_XXXX.csv
   python scripts\predict_with_optional_yutura.py --trend trend_data\...csv --use-yutura data\features_yutura_XXXX.csv --out data\preds.csv
   ```

注意
- `data/` や学習済みモデル（*.pkl）など大きいファイルはコミットしないか Git LFS を使って管理してください。
- APIキーなどの秘密情報は `.env` 等で管理し、絶対にコミットしないでください。

ライセンス
- MIT
