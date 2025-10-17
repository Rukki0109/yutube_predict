#!/usr/bin/env python3
"""
Extract vocabulary/phrases from a yutura news CSV (titles) and save a date-stamped CSV.

Behavior:
- Reads input CSV (expects column `title`).
- Extracts: quoted phrases inside 「」, and contiguous tokens of Japanese characters or ASCII words (length 2..12).
- Counts frequencies, collects example titles for each phrase, and writes CSV: phrase,count,score,examples
- Default output filename is derived from input filename date if present, otherwise today's date.

Usage:
  python scripts\extract_yutura_vocab.py --in data\yutura_news_pages_20251010_1-5.csv

"""
import argparse
import csv
import os
import re
from collections import Counter, defaultdict
from datetime import datetime

import pandas as pd


RE_QUOTE = re.compile(r'【([^】]{1,80})】|「([^」]{1,80})」|"([^"]{1,80})"')
# Japanese character runs (kanji, hiragana, katakana) or ascii words
RE_TOKEN = re.compile(r'[一-龥]+|[ぁ-ん]+|[ァ-ヴー]+|[A-Za-z0-9]+')


def extract_phrases_from_title(title):
    phrases = []
    if not isinstance(title, str):
        return phrases

    # quoted phrases
    for m in RE_QUOTE.finditer(title):
        for g in m.groups():
            if g:
                s = g.strip()
                if len(s) >= 2:
                    phrases.append(s)

    # token runs
    for m in RE_TOKEN.finditer(title):
        tok = m.group(0)
        # filter length
        if 2 <= len(tok) <= 12:
            phrases.append(tok)

    return phrases


def derive_output_path(input_path, out_arg=None):
    # try to find YYYYMMDD in input filename
    base = os.path.basename(input_path)
    m = re.search(r'(20\d{6})', base)
    date = m.group(1) if m else datetime.now().strftime('%Y%m%d')
    if out_arg:
        return out_arg
    name = f'yutura_vocab_{date}_' + os.path.splitext(base)[0] + '.csv'
    return os.path.join('data', name)


def main():
    parser = argparse.ArgumentParser(description='Extract vocab from yutura news CSV')
    parser.add_argument('--in', dest='in_csv', required=True)
    parser.add_argument('--out', dest='out_csv', default=None)
    args = parser.parse_args()

    df = pd.read_csv(args.in_csv)
    titles = df['title'].fillna('').astype(str).tolist()

    counter = Counter()
    examples = defaultdict(list)

    for t in titles:
        phrases = extract_phrases_from_title(t)
        seen = set()
        for p in phrases:
            # normalize whitespace
            p_norm = re.sub(r'\s+', ' ', p).strip()
            if p_norm in seen:
                continue
            seen.add(p_norm)
            counter[p_norm] += 1
            if len(examples[p_norm]) < 3:
                examples[p_norm].append(t)

    total = sum(counter.values())
    rows = []
    for phrase, cnt in counter.most_common():
        score = cnt / len(titles)  # fraction of titles containing it
        rows.append({'phrase': phrase, 'count': cnt, 'score': round(score, 4), 'examples': ' || '.join(examples[phrase])})

    out_path = derive_output_path(args.in_csv, args.out_csv)
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    out_df = pd.DataFrame(rows)
    out_df.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f'Wrote {len(out_df)} phrases to {out_path}')


if __name__ == '__main__':
    main()
