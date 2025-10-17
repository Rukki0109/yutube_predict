# yt_trendlab

YouTubeの**急上昇(Trending)特徴量**を既存の
- サムネイル特徴（明度・色・顔数・白強調＝telop_proxy、KMeans 5色比）
- 投稿日時特徴（曜日・時間・週末・月初/末）
- タイトルTF‑IDF

と統合して、再生回数を予測・評価するためのミニパッケージです。  
**`days_since_posted` はリーク防止のため使用しません。**

---

## インストール/前提

- Python 3.9+ 推奨
- 依存（ノートブックで）:
  ```bash
  %pip install google-api-python-client pandas scikit-learn janome opencv-python pillow mediapipe tqdm seaborn
  ```

- **YouTube Data API v3 のAPIキー**を用意し、環境変数に設定（どれか1つでOK）
  ```python
  import os
  os.environ["YT_API_KEY"] = "AIza...あなたのキー..."  # 推奨
  # 代替: os.environ["API_KEY"] / os.environ["YOUTUBE_API_KEY"]
  ```

> 初回は急上昇CSVが1本も無い場合、自動で**当日分スナップショット**を取得します。  
> 以降は `trending_JP_YYYYMMDD.csv` が日次で貯まり、直近N日（デフォ14日）から“流行語辞書”を生成します。

---

## ディレクトリ構成（例）

```
C:\Users\Owner\youtube\
  ├─ youtube_dataset_20250829.xlsx
  ├─ test0829.ipynb
  ├─ yt_trend\                 ← 既存(任意)：get_trending.py / trend_features.py がある場合
  ├─ code\                     ← 既存(任意)：上と同内容ならそのままでも可
  └─ yt_trendlab\              ← 本パッケージ（この README はここ）
      ├─ __init__.py
      ├─ pipeline.py
      ├─ thumbnail_features.py
      ├─ trending_utils.py
      ├─ text_features.py
      └─ modeling.py
```

> `yt_trendlab/trending_utils.py` は、まず `yt_trend` パッケージを探し、無ければ `./code/*.py` を動的ロードします。

---

## クイックスタート（ノートブック最短）

```python
import os, sys
sys.path.append(r"C:\Users\Owner\youtube")   # 親フォルダをPATHに追加
os.environ["YT_API_KEY"] = "AIza...あなたのキー..."

from yt_trendlab import run_all
model, df_result, metrics, imp_top = run_all(
    xlsx_path="youtube_dataset_20250829.xlsx",
    cutoff="2025-07-01",
    tfidf_max_features=300
)
print(metrics)        # {'rmse_log': ..., 'rmse_raw': ...}
display(imp_top)      # 重要度TOP30
display(df_result.head(10))  # 直近サンプルの予測と誤差
```

---

## 何をしているか（概要）

1. **データ読み込み**
   - タイトル欠損埋め、カテゴリID/再生数の数値化、`publishedAt` をUTCで `datetime` 化、`duration>60s` でShorts除外。

2. **サムネイル特徴**
   - 明度/色平均/HSV平均、KMeans(5色)比率、白画素比（telop_proxy）、MediaPipe顔数。

3. **投稿日時特徴**
   - 曜日・時間・週末・月初/末（※ `days_since_posted` は使わない）。

4. **急上昇(Trending)特徴**
   - `trending_JP_YYYYMMDD.csv` の直近N日から流行語を抽出し、
     - `trend_overlap_count`（一致語数）
     - `trend_overlap_ratio`（一致率）
     - `trend_cosine_sim`（BoWで急上昇集合との平均コサイン類似度）
     を付与。  
   - CSVが無い場合は、APIキーがあればその場で当日分を取得。

5. **タイトルTF‑IDF**
   - Janomeで名詞/動詞/形容詞を抽出、`max_features` は引数で調整可能。

6. **学習・評価**
   - 時系列分割（`cutoff`）→ RandomForest で学習。  
   - 予測は log→exp 戻し、`RMSE(log)` と `RMSE(raw)` を出力。  
   - 重要度TOP30と、予測 vs 実測のテーブルを返す。

---

## よくあるQ&A / トラブルシュート

- **`HttpError: API key not valid`**  
  → `os.environ["YT_API_KEY"]` が実キーか、Google Cloudで **YouTube Data API v3 を有効化**しているか確認。  
  → ノートブックの**同じカーネルで再設定**が必要（再起動後は再実行）。

- **`ModuleNotFoundError: yt_trend`**  
  → `yt_trendlab/trending_utils.py` は自動で `./code/*.py` をロードします。  
     どちらも無ければ `get_trending.py` / `trend_features.py` を配置してください。

- **OpenCV/MediaPipe のエラー**  
  → `opencv-python` と `mediapipe` のバージョン互換を確認。GPUは不要です。

- **精度が物足りない**  
  - TF‑IDF語彙を増やす（例：300→1000）  
  - `TREND_USE_LAST_N`（7〜21日）や `TREND_TOPK` をチューニング  
  - モデルを LightGBM/XGBoost に置き換え（構成はそのまま流用可）  
  - 後段キャリブレーション：学習後に `y_true = a*y_pred + b` を検証でフィットして補正

---

## API（主要関数）

- `run_all(xlsx_path, cutoff, tfidf_max_features)`  
  全処理を実行し、`(model, df_result, metrics, imp_top)` を返す。

- `ensure_trending_snapshot_if_missing()`  
  `trending_JP_*.csv` が無い場合、APIキーを用いて当日分を取得して保存。

- `add_trend_features(titles: pd.Series) -> pd.DataFrame`  
  直近N日から作った流行語辞書に基づき、3特徴量を返す。

- `extract_all_thumbnail_features_mediapipe(url) -> list`  
  画像URLからサムネ特徴量を抽出。列名は `THUMBNAIL_COLS`。

---

## ライセンス
研究/学習目的を想定。YouTube Data APIの利用規約に従って使用してください。
