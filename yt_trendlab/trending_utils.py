# -*- coding: utf-8 -*-
import os, re, glob, pathlib, importlib.util, inspect
import pandas as pd
from datetime import datetime

TREND_CSV_GLOB = "trending_JP_*.csv"
TREND_USE_LAST_N = 14
TREND_TOPK = 500
TREND_VOCAB_PATH = "trend_vocab.json"

# fetch_trending / trend_features のローダ
def _load_trend_modules():
    try:
        from yt_trend.get_trending import fetch_trending as _fetch
        from yt_trend.trend_features import (
            build_trend_vocab_from_csvs as _build_vocab,
            save_trend_vocab_json as _save_vocab,
            load_trend_vocab_json as _load_vocab,
            title_trend_features as _title_feats,
        )
        return _fetch, _build_vocab, _save_vocab, _load_vocab, _title_feats
    except ModuleNotFoundError:
        base = pathlib.Path.cwd() / "code"
        gt, tf = base / "get_trending.py", base / "trend_features.py"
        def _load(name, path):
            spec = importlib.util.spec_from_file_location(name, str(path))
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod
        if gt.exists() and tf.exists():
            gt = _load("yt_trend_get_trending", gt)
            tf = _load("yt_trend_trend_features", tf)
            return gt.fetch_trending, tf.build_trend_vocab_from_csvs, tf.save_trend_vocab_json, tf.load_trend_vocab_json, tf.title_trend_features
        raise

_fetch, _build_vocab, _save_vocab, _load_vocab, _title_feats = _load_trend_modules()

def ensure_trending_snapshot_if_missing(api_key_env="YT_API_KEY", region="JP", max_results=200, category_id=None):
    csvs = glob.glob(TREND_CSV_GLOB)
    if len(csvs)>0: return
    api_key = os.getenv(api_key_env) or os.getenv("API_KEY") or os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        print("⚠️ 急上昇CSVが無く、APIキー未設定のため自動取得をスキップ"); return
    print("ℹ️ 急上昇CSVが無いので、その場取得します…")
    # _fetch may be either fetch_trending(api_key, region_code, max_results)
    # or fetch_trending_with_category(api_key, region_code, category_id, max_results).
    # Try to call with category if provided, otherwise fall back.
    df = None
    if category_id is not None:
        try:
            # Try positional (api_key, region, category_id, max_results)
            df = _fetch(api_key, region, category_id, max_results)
        except TypeError:
            # Fallback: try keyword invocation if supported
            try:
                df = _fetch(api_key, region_code=region, category_id=category_id, max_results=max_results)
            except Exception:
                # Last resort: call without category
                df = _fetch(api_key, region_code=region, max_results=max_results)
    else:
        # No category requested: call the simple signature
        try:
            df = _fetch(api_key, region_code=region, max_results=max_results)
        except TypeError:
            # Some variants might not accept keyword args; try positional
            df = _fetch(api_key, region, max_results)
    out = f"trending_JP_{datetime.now().strftime('%Y%m%d')}.csv"
    df.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"✅ Saved: {out} (rows={len(df)})")

def add_trend_features(titles: pd.Series, verbose=True) -> pd.DataFrame:
    if verbose:
        print(f"[yt_trendlab] Building trend features for {len(titles)} titles...")
    csvs = sorted(glob.glob(TREND_CSV_GLOB))
    if len(csvs)==0:
        if verbose:
            print("[yt_trendlab] Trend features done.")
        return pd.DataFrame({"trend_overlap_count":[0]*len(titles),
                             "trend_overlap_ratio":[0.0]*len(titles),
                             "trend_cosine_sim":[0.0]*len(titles)})
    def key(p):
        m = re.search(r"(\d{8})", os.path.basename(p)); return m.group(1) if m else "00000000"
    csvs = sorted(csvs, key=key)[-TREND_USE_LAST_N:]
    if os.path.exists(TREND_VOCAB_PATH):
        hot = _load_vocab(TREND_VOCAB_PATH)
        _, trend_titles = _build_vocab(csvs, top_k=TREND_TOPK)
    else:
        hot, trend_titles = _build_vocab(csvs, top_k=TREND_TOPK)
        _save_vocab(hot, TREND_VOCAB_PATH)
    feats = titles.fillna("").apply(lambda t: _title_feats(t, hot, trend_titles_for_bow=trend_titles))
    if verbose:
        print("[yt_trendlab] Trend features done.")
    return pd.DataFrame(list(feats.values))
