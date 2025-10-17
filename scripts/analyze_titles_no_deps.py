#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
analyze_titles_no_deps.py
-------------------------
依存ライブラリなしで動作する簡易タイトル解析。
正規表現で日本語（漢字・ひらがな・カタカナ）と英単語を抽出し、TF-IDFを自前実装して上位語を出力します。

出力: yt_trend/title_tfidf_top20_nondeps.csv
"""
import csv
from pathlib import Path
import re
import math

ROOT = Path(__file__).resolve().parents[1]
IN_CSV = ROOT / "yt_trend" / "trending_titles_50.csv"
OUT_CSV = ROOT / "yt_trend" / "title_tfidf_top20_nondeps.csv"

TOK_PATTERNS = [
    r"[\u4E00-\u9FFF]+",  # CJK Unified Ideographs (漢字)
    r"[\u3040-\u309F]+",  # Hiragana
    r"[\u30A0-\u30FF]+",  # Katakana
    r"[A-Za-z]+",          # Latin words
    r"[0-9]+"
]
TOK_RE = re.compile("|".join(TOK_PATTERNS))

def load_titles(path):
    docs = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            docs.append(row.get("title", "") or "")
    return docs

def tokenize(text):
    return [m.group(0) for m in TOK_RE.finditer(text)]

def build_tfidf(docs):
    tokenized = [tokenize(d) for d in docs]
    N = len(tokenized)
    df = {}
    tfs = []
    for tokens in tokenized:
        counts = {}
        for t in tokens:
            counts[t] = counts.get(t, 0) + 1
        tfs.append((counts, len(tokens)))
        for t in set(tokens):
            df[t] = df.get(t, 0) + 1

    idf = {t: math.log((N / df[t]) + 1) for t in df}

    # compute corpus-level score = sum of tf-idf across docs
    scores = {}
    for counts, total in tfs:
        if total == 0:
            continue
        for t, c in counts.items():
            tf = c / total
            scores[t] = scores.get(t, 0.0) + tf * idf.get(t, 0.0)
    return scores

def main():
    if not IN_CSV.exists():
        print(f"Input not found: {IN_CSV}")
        return
    docs = load_titles(IN_CSV)
    scores = build_tfidf(docs)
    items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    top20 = items[:20]
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['term','score'])
        for term, score in top20:
            writer.writerow([term, f"{score:.6f}"])
    print(f"Wrote top20 to: {OUT_CSV}")
    for term, score in top20:
        print(f"{term}: {score:.6f}")

if __name__ == '__main__':
    main()
