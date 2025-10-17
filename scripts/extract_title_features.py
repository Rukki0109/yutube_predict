#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
extract_title_features.py
-------------------------
`yt_trend/trending_titles_50.csv` を読み、各タイトルについて以下の特徴量を計算して
`yt_trend/title_features_50.csv` に保存します。

特徴量:
 - title_len_chars: タイトルの文字数
 - title_word_count: 正規表現ベースのトークン数
 - english_ratio: 英字文字の比率
 - has_number: 数字を含むか
 - top_keyword_*: `title_tfidf_top20_nondeps.csv` の上位語が含まれるかのフラグ
 - punctuation_count: 記号の数

"""
import csv
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
IN_CSV = ROOT / "yt_trend" / "trending_titles_50.csv"
TFIDF_TOP = ROOT / "yt_trend" / "title_tfidf_top20_nondeps.csv"
OUT_CSV = ROOT / "yt_trend" / "title_features_50.csv"

TOK_RE = re.compile(r"[\u4E00-\u9FFF]+|[\u3040-\u309F]+|[\u30A0-\u30FF]+|[A-Za-z]+|[0-9]+")
ENG_RE = re.compile(r"[A-Za-z]")
NUM_RE = re.compile(r"[0-9]")
PUNC_RE = re.compile(r'[!"#$%&\'()*+,\-./:;<=>?@\[\\\]^_`{|}~]')

def load_top_terms(path):
    terms = []
    if not path.exists():
        return terms
    with path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            terms.append(row['term'])
    return terms

def tokenize(text):
    return [m.group(0) for m in TOK_RE.finditer(text)]

def compute_features(title, top_terms):
    title = title or ""
    chars = len(title)
    tokens = tokenize(title)
    word_count = len(tokens)
    eng_chars = len(ENG_RE.findall(title))
    english_ratio = eng_chars / chars if chars>0 else 0.0
    has_number = int(bool(NUM_RE.search(title)))
    punc_count = len(PUNC_RE.findall(title))
    features = {
        'title_len_chars': chars,
        'title_word_count': word_count,
        'english_ratio': round(english_ratio, 4),
        'has_number': has_number,
        'punctuation_count': punc_count
    }
    lowered = title.lower()
    for t in top_terms:
        key = f"top_keyword_{t}"
        features[key] = int(t.lower() in lowered)
    return features

def main():
    top_terms = load_top_terms(TFIDF_TOP)
    if not IN_CSV.exists():
        print(f"Input not found: {IN_CSV}")
        return
    out_header = ['videoId','title','channelTitle','viewCount','snapshot_at_utc'] + ['title_len_chars','title_word_count','english_ratio','has_number','punctuation_count'] + [f"top_keyword_{t}" for t in top_terms]
    with IN_CSV.open('r', encoding='utf-8') as inf, OUT_CSV.open('w', encoding='utf-8', newline='') as outf:
        reader = csv.DictReader(inf)
        writer = csv.DictWriter(outf, fieldnames=out_header)
        writer.writeheader()
        for row in reader:
            title = row.get('title','')
            feats = compute_features(title, top_terms)
            out_row = {k: row.get(k,'') for k in ['videoId','title','channelTitle','viewCount','snapshot_at_utc']}
            out_row.update(feats)
            writer.writerow(out_row)
    print(f"Wrote features to: {OUT_CSV}")

if __name__ == '__main__':
    main()
