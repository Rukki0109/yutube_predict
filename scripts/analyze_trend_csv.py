#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
analyze_trend_csv.py
--------------------
指定された trending CSV を解析し、要約統計、タイトルの TF-IDF 上位語、
タイトル特徴量（title_features）を出力します。

使い方:
  python scripts/analyze_trend_csv.py --in trend_data/trending_...csv

出力:
  - yt_trend/title_tfidf_top20.csv
  - yt_trend/title_features_50.csv
  - 標準出力に要約統計を表示
"""
import argparse
import csv
from pathlib import Path
import pandas as pd
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / 'yt_trend'
OUT_DIR.mkdir(parents=True, exist_ok=True)

def load_df(path: Path):
    return pd.read_csv(path, encoding='utf-8-sig')

def tokenize_japanese_simple(text):
    import re
    TOK_PATTERNS = [r"[\u4E00-\u9FFF]+", r"[\u3040-\u309F]+", r"[\u30A0-\u30FF]+", r"[A-Za-z]+", r"[0-9]+"]
    TOK_RE = re.compile("|".join(TOK_PATTERNS))
    return [m.group(0) for m in TOK_RE.finditer(text or "")]

def compute_tfidf(titles):
    # Prefer janome + sklearn if available
    try:
        from janome.tokenizer import Tokenizer
        from sklearn.feature_extraction.text import TfidfVectorizer
        t = Tokenizer()
        docs = []
        for txt in titles:
            tokens = [tok.surface for tok in t.tokenize(txt or "") if tok.part_of_speech.split(',')[0] in ('名詞','動詞','形容詞')]
            docs.append(' '.join(tokens))
        vec = TfidfVectorizer(max_features=1000)
        X = vec.fit_transform(docs)
        feature_names = vec.get_feature_names_out()
        scores = X.sum(axis=0).A1
        pairs = list(zip(feature_names, scores))
        pairs.sort(key=lambda x: x[1], reverse=True)
        return pairs[:20]
    except Exception:
        # fallback simple implementation
        from collections import Counter
        token_lists = [tokenize_japanese_simple(t or "") for t in titles]
        df = len(token_lists)
        dfreq = {}
        tfs = []
        for tokens in token_lists:
            counts = {}
            for tok in tokens:
                counts[tok] = counts.get(tok, 0) + 1
            tfs.append((counts, len(tokens)))
            for tok in set(tokens):
                dfreq[tok] = dfreq.get(tok, 0) + 1
        import math
        idf = {t: math.log((df / dfreq[t]) + 1) for t in dfreq}
        scores = {}
        for counts, total in tfs:
            if total == 0:
                continue
            for t, c in counts.items():
                tf = c / total
                scores[t] = scores.get(t, 0.0) + tf * idf.get(t, 0.0)
        items = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return items[:20]

def save_top20(pairs, out_path: Path):
    with out_path.open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['term','score'])
        for term, score in pairs:
            writer.writerow([term, score])

def extract_title_features(df: pd.DataFrame, top_terms):
    import re
    TOK_RE = re.compile(r"[\u4E00-\u9FFF]+|[\u3040-\u309F]+|[\u30A0-\u30FF]+|[A-Za-z]+|[0-9]+")
    ENG_RE = re.compile(r"[A-Za-z]")
    NUM_RE = re.compile(r"[0-9]")
    PUNC_RE = re.compile(r'[!"#$%&\'"()*+,\-./:;<=>?@\[\\\]^_`{|}~]')

    def tokenize(text):
        return [m.group(0) for m in TOK_RE.finditer(text or "")]

    rows = []
    for _, row in df.iterrows():
        title = row.get('title', '') or ''
        chars = len(title)
        tokens = tokenize(title)
        word_count = len(tokens)
        eng_chars = len(ENG_RE.findall(title))
        english_ratio = eng_chars / chars if chars>0 else 0.0
        has_number = int(bool(NUM_RE.search(title)))
        punc_count = len(PUNC_RE.findall(title))
        lowered = title.lower()
        feats = {
            'videoId': row.get('videoId',''),
            'title': title,
            'channelTitle': row.get('channelTitle',''),
            'viewCount': row.get('viewCount',''),
            'snapshot_at_utc': row.get('snapshot_at_utc',''),
            'title_len_chars': chars,
            'title_word_count': word_count,
            'english_ratio': round(english_ratio,4),
            'has_number': has_number,
            'punctuation_count': punc_count
        }
        for t, _ in top_terms:
            feats[f'top_keyword_{t}'] = int(t.lower() in lowered)
        rows.append(feats)
    return pd.DataFrame(rows)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--in', dest='infile', required=True)
    args = parser.parse_args()
    in_path = Path(args.infile)
    if not in_path.exists():
        print('Input not found:', in_path); sys.exit(1)
    df = load_df(in_path)
    print('Loaded:', in_path, 'rows=', len(df))
    # summary
    if 'viewCount' in df.columns:
        df['viewCount'] = pd.to_numeric(df['viewCount'], errors='coerce')
        print('\nViewCount summary:')
        print(df['viewCount'].describe())
    # titles
    titles = df['title'].fillna('').tolist()
    top20 = compute_tfidf(titles)
    out_top20 = OUT_DIR / 'title_tfidf_top20.csv'
    save_top20(top20, out_top20)
    print('\nWrote TF-IDF top20 to:', out_top20)
    # title features
    feats_df = extract_title_features(df, top20)
    out_feats = OUT_DIR / 'title_features_from_trend.csv'
    feats_df.to_csv(out_feats, index=False, encoding='utf-8-sig')
    print('Wrote title features to:', out_feats)

if __name__ == '__main__':
    main()
