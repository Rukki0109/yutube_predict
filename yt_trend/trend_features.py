#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
trend_features.py
-----------------
急上昇（Trending）スナップショット CSV 群から「今の流行語」辞書を作り、
任意のタイトル文字列に対して以下の特徴量を返します:

- trend_overlap_count: 流行語との一致語数
- trend_overlap_ratio: そのタイトルの形態素数に対する一致比
- trend_cosine_sim:    急上昇タイトル集合との Bag-of-Words コサイン類似度

使い方（例）:
  python trend_features.py --trending_csvs trending_JP_20250925.csv trending_JP_20250926.csv --title "阿修羅モード突入！ガチ喧嘩で絶句の瞬間"

学習パイプライン統合方針:
1) 日次で get_trending.py を実行して CSV を貯める
2) 直近N日（例: 7日 or 14日）の CSV を読み込み、「trend_vocab.json」を生成
3) feature_extraction.py 内で各サンプルのタイトル→ trend特徴量を計算して列を追加
4) 予測時（predict_view_count.py）でも同じ trend_vocab.json を使って特徴量を追加
"""
import argparse
import json
import os
import re
from collections import Counter
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# --- 超軽量な日本語トークナイザ（スペース/記号で分割）---
# 精密には Janome / Sudachi を推奨。既存プロジェクトで Janome を使っていれば差し替え可能。
TOKEN_PATTERN = re.compile(r"[^\wぁ-んァ-ン一-龯]+")

def tokenize(text: str):
    text = text.lower().strip()
    text = TOKEN_PATTERN.sub(" ", text)
    toks = [t for t in text.split() if t]
    return toks

def build_trend_vocab_from_csvs(csv_paths, top_k: int=500):
    """
    複数日の trending CSV を読み、タイトルから出現頻度の高い語を top_k 抜き出す。
    返り値:
      - hotwords: list[str] 上位単語（重複除去）
      - titles: list[str]  全タイトル（BoW用）
    """
    titles = []
    for p in csv_paths:
        if not os.path.exists(p):
            continue
        df = pd.read_csv(p)
        titles.extend(df["title"].fillna("").tolist())
    # 単語頻度
    cnt = Counter()
    for t in titles:
        cnt.update(tokenize(t))
    # 極端に短い/一般語を雑に除外（調整可能）
    stop = set(["の","に","を","が","で","と","は","も","や","ww","www","w","the","and","for","a","to","in"])
    hotwords = [w for w,_c in cnt.most_common(top_k*2) if (len(w) >= 2 and w not in stop)]
    hotwords = hotwords[:top_k]
    return hotwords, titles

def save_trend_vocab_json(hotwords, json_path="trend_vocab.json"):
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"hotwords": hotwords}, f, ensure_ascii=False, indent=2)
    return json_path

def load_trend_vocab_json(json_path="trend_vocab.json"):
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)["hotwords"]

def title_trend_features(title: str, hotwords, trend_titles_for_bow=None):
    toks = tokenize(title)
    if not toks:
        return {"trend_overlap_count": 0, "trend_overlap_ratio": 0.0, "trend_cosine_sim": 0.0}

    # 1) overlap
    hw = set(hotwords)
    overlap = sum(1 for t in toks if t in hw)
    ratio = overlap / max(1, len(toks))

    # 2) cosine (BoW vs trending corpus)
    cosine = 0.0
    if trend_titles_for_bow is not None and len(trend_titles_for_bow) > 0:
        cv = CountVectorizer(tokenizer=tokenize)
        bow_corpus = trend_titles_for_bow + [title]
        X = cv.fit_transform(bow_corpus)
        sim = cosine_similarity(X[-1], X[:-1]).ravel()
        cosine = float(np.mean(sim))  # タイトルと急上昇集合の平均類似度

    return {
        "trend_overlap_count": int(overlap),
        "trend_overlap_ratio": float(ratio),
        "trend_cosine_sim": float(cosine)
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--trending_csvs", nargs="+", required=True)
    ap.add_argument("--title", type=str, default=None)
    ap.add_argument("--topk", type=int, default=500)
    ap.add_argument("--out_vocab", default="trend_vocab.json")
    args = ap.parse_args()

    hotwords, titles = build_trend_vocab_from_csvs(args.trending_csvs, top_k=args.topk)
    save_trend_vocab_json(hotwords, args.out_vocab)
    print(f"✅ Saved vocab: {args.out_vocab} (hotwords={len(hotwords)})")

    if args.title:
        feats = title_trend_features(args.title, hotwords, titles)
        print("🔎 Features for title:", args.title)
        print(feats)

if __name__ == "__main__":
    main()
