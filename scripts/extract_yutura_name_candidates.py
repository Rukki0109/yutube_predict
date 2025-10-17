#!/usr/bin/env python3
"""
Extract candidate person/channel names from yutura news titles using rule-based heuristics.

Output CSV columns:
  rank,page,title,url,date,source_page,candidate,kind,score

kind: one of ['person', 'channel', 'org', 'unknown'] (heuristic)
score: heuristic confidence (0-1)
"""
import argparse
import csv
import logging
import os
import re
from typing import List, Tuple

import pandas as pd


# Simpler regexes using Unicode ranges for Japanese scripts (compatible with Python's re)
RE_PATTERNS = [
    # 「YouTuber X」「VTuber X」「実況者 X」などの明示的なラベル
    (re.compile(r"(?:YouTuber|VTuber|実況者)\s*([A-Za-z0-9\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FFー☆★\-\u30FB]+)"), 'channel'),
    # 名前が文頭に来て区切り（、や句読点）や助詞が続くケース: 「ヒカル、〜」「ヒカルが〜」
    (re.compile(r"\b([\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FFA-Za-z0-9☆★]{2,15})[、,，\s]*(?:が|に|を|と|の)"), 'person'),
    # 肩書きを含む呼称: "松浦会長" や "社長" など
    (re.compile(r"([\u4E00-\u9FFF]{2,10}(?:会長|社長|代表|氏|さん))"), 'person'),
    # 短めの英字ニックネーム
    (re.compile(r"\b([A-Za-z0-9_]{3,30})\b"), 'channel'),
]


def normalize_candidate(s: str) -> str:
    s = s.strip()
    # normalize spaces and punctuation
    s = re.sub(r"[\u3000\s]+", " ", s)
    s = s.replace('（', '(').replace('）', ')')
    return s


def extract_candidates_from_title(title: str) -> List[Tuple[str, str, float]]:
    """Return list of (candidate, kind, score)"""
    candidates = []
    if not isinstance(title, str):
        return candidates

    t = title

    # heuristic 1: explicit marker patterns
    for pat, kind in RE_PATTERNS:
        for m in pat.finditer(t):
            cand = m.group(1)
            cand = normalize_candidate(cand)
            # score heuristic: longer tokens and tokens with Kanji get higher score
            score = 0.6 + min(len(cand) / 20.0, 0.4)
            if re.search(r"[一-龥]", cand):
                score += 0.1
            score = min(score, 1.0)
            candidates.append((cand, kind, round(score, 2)))

    # heuristic 2: titles containing quotes or special markers like 「」
    quotes = re.findall(r'「([^」]{2,30})」', t)
    for q in quotes:
        qn = normalize_candidate(q)
        candidates.append((qn, 'unknown', 0.4))

    # heuristic 3: single tokens of Katakana or mixed used as names
    katakana_matches = re.findall(r'([ァ-ン]{2,20})', t)
    for km in katakana_matches:
        kmn = normalize_candidate(km)
        candidates.append((kmn, 'person', 0.5))

    # dedupe while preserving order
    seen = set()
    out = []
    for c, k, s in candidates:
        key = (c.lower(), k)
        if key in seen:
            continue
        seen.add(key)
        out.append((c, k, s))

    return out


def process(in_csv: str, out_csv: str):
    df = pd.read_csv(in_csv)
    rows = []
    for _, r in df.iterrows():
        title = r.get('title', '')
        url = r.get('url', '')
        page = r.get('page', '')
        rank = r.get('rank', '')
        date = r.get('date', '')

        candidates = extract_candidates_from_title(title)
        if not candidates:
            rows.append({
                'rank': rank, 'page': page, 'title': title, 'url': url, 'date': date,
                'candidate': '', 'kind': 'none', 'score': 0.0
            })
        else:
            for cand, kind, score in candidates:
                rows.append({
                    'rank': rank, 'page': page, 'title': title, 'url': url, 'date': date,
                    'candidate': cand, 'kind': kind, 'score': score
                })

    out_df = pd.DataFrame(rows)
    os.makedirs(os.path.dirname(out_csv) or '.', exist_ok=True)
    out_df.to_csv(out_csv, index=False, encoding='utf-8-sig')
    logging.info(f"Wrote {len(out_df)} candidate rows to {out_csv}")


def main():
    parser = argparse.ArgumentParser(description='Extract name/channel candidates from yutura CSV')
    parser.add_argument('--in', dest='in_csv', default='data/yutura_news_pages_1-5.csv')
    parser.add_argument('--out', dest='out_csv', default='data/yutura_name_candidates_1-5.csv')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    process(args.in_csv, args.out_csv)


if __name__ == '__main__':
    main()
