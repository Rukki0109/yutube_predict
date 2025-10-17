#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
analyze_titles.py
-----------------
`yt_trend/trending_titles_50.csv` を読み、形態素解析（Janome）でトークン化して TF-IDF を計算。
上位20語を表示し、結果を `yt_trend/title_tfidf_top20.csv` に保存します。
"""
import csv
from pathlib import Path
from collections import Counter
import sys

ROOT = Path(__file__).resolve().parents[1]
IN_CSV = ROOT / "yt_trend" / "trending_titles_50.csv"
OUT_CSV = ROOT / "yt_trend" / "title_tfidf_top20.csv"

try:
    from janome.tokenizer import Tokenizer
except Exception:
    print("janome is required. Install with: pip install janome")
    sys.exit(1)

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
except Exception:
    print("scikit-learn is required. Install with: pip install scikit-learn")
    sys.exit(1)

def load_titles(in_csv: Path):
    titles = []
    with in_csv.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            titles.append(row.get("title", ""))
    return titles

def tokenize_japanese(texts):
    t = Tokenizer()
    docs = []
    for txt in texts:
        tokens = [tok.surface for tok in t.tokenize(txt) if tok.part_of_speech.split(',')[0] in ('名詞','動詞','形容詞')]
        docs.append(' '.join(tokens))
    return docs

def main():
    if not IN_CSV.exists():
        print(f"Input not found: {IN_CSV}")
        return
    titles = load_titles(IN_CSV)
    docs = tokenize_japanese(titles)
    vec = TfidfVectorizer(max_features=1000)
    X = vec.fit_transform(docs)
    feature_names = vec.get_feature_names_out()
    # Sum tfidf across documents to get global importance
    scores = X.sum(axis=0).A1
    pairs = list(zip(feature_names, scores))
    pairs.sort(key=lambda x: x[1], reverse=True)
    top20 = pairs[:20]
    # Save
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['term','score'])
        for term, score in top20:
            writer.writerow([term, score])
    print(f"Wrote top20 to: {OUT_CSV}")
    for term, score in top20:
        print(f"{term}: {score:.4f}")

if __name__ == '__main__':
    main()
