#!/usr/bin/env python3
"""Quick inspector for data/yutura_name_candidates_1-5.csv

Prints summary statistics and examples to stdout.
"""
from collections import Counter, defaultdict
import pandas as pd
import re

IN = 'data/yutura_name_candidates_1-5.csv'


def short(x, n=80):
    return x if len(x) <= n else x[:n-1] + '…'


def main():
    df = pd.read_csv(IN)
    total_rows = len(df)
    unique_titles = df['title'].nunique()
    unique_candidates = df[df['candidate'].notna() & (df['candidate']!='')]['candidate'].nunique()

    # candidates per title
    cp = df.groupby('title').apply(lambda g: g[g['candidate'].notna() & (g['candidate']!='')].shape[0])
    avg_cp = cp.mean()
    median_cp = cp.median()

    kind_counts = df['kind'].value_counts()

    # top candidates by frequency
    cand_counter = Counter()
    cand_scores = defaultdict(list)
    for _, r in df.iterrows():
        c = r['candidate'] if pd.notna(r['candidate']) else ''
        if c:
            cand_counter[c] += 1
            try:
                cand_scores[c].append(float(r.get('score', 0)))
            except Exception:
                pass

    top10 = cand_counter.most_common(20)

    # high-confidence examples
    high_conf = df[(df['score']>=0.9) & (df['candidate'].notna()) & (df['candidate']!='')]
    low_conf = df[(df['score']<=0.4) & (df['candidate'].notna()) & (df['candidate']!='')]

    print(f"Input: {IN}")
    print(f"Total rows: {total_rows}")
    print(f"Unique titles: {unique_titles}")
    print(f"Unique non-empty candidates: {unique_candidates}")
    print(f"Avg candidates per title (including zeros): {avg_cp:.2f}, median: {median_cp}")
    print('\nKinds distribution:')
    for k,v in kind_counts.items():
        print(f"  {k}: {v}")

    print('\nTop candidates (by frequency, up to 20):')
    for c, cnt in top10:
        avg_score = sum(cand_scores[c]) / len(cand_scores[c]) if cand_scores[c] else 0
        print(f"  {cnt:3d}x  {short(c,60):60}  avg_score={avg_score:.2f}")

    print('\nHigh-confidence examples (score>=0.9), up to 10:')
    for _, r in high_conf.head(10).iterrows():
        print(f"  [{r['score']}] {short(r['candidate'],60):60}  -- title: {short(r['title'],80)}")

    print('\nLow-confidence/noisy examples (score<=0.4), up to 15:')
    show=0
    for _, r in low_conf.iterrows():
        c=r['candidate']
        if len(str(c))>1 and re.search(r'[一-龥ぁ-んァ-ンA-Za-z0-9]', str(c)):
            print(f"  [{r['score']}] {short(c,60):60}  -- title: {short(r['title'],80)}")
            show+=1
            if show>=15:
                break


if __name__ == '__main__':
    main()
