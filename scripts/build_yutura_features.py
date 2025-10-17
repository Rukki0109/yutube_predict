#!/usr/bin/env python3
"""
Minimal prototype: build yutura-derived features for each video in a trend CSV.

Usage:
  python scripts\build_yutura_features.py --trend trend_data\trending_JP_category24_no_shorts_20251009.csv --yutura data\yutura_news_pages_20251010_1-5.csv --out data\features_yutura_20251009.csv

Features produced (per videoId):
- mention_count_3d, mention_any_3d (Jaccard threshold 0.25)
- max_jaccard_3d
- channel_mentioned_3d (channelTitle substring or candidate match)
- days_since_last_mention_3d
 (and same for 7d suffix)

This is intentionally simple and dependency-light.
"""
import argparse
import os
import re
from datetime import datetime, timedelta
from collections import defaultdict

import pandas as pd


def normalize_text(s: str) -> str:
    if not isinstance(s, str):
        return ""
    s = s.strip()
    # to half-width for ascii digits/letters roughly
    s = s.replace('\u3000', ' ')
    s = re.sub(r'[\s\u00A0]+', ' ', s)
    return s


def tokenize(s: str):
    s = normalize_text(s)
    # extract Japanese runs or ascii words/numbers
    toks = re.findall(r'[一-龥ぁ-んァ-ヴー]+|[A-Za-z0-9]+', s)
    return [t for t in toks if t]


def jaccard(a, b):
    if not a or not b:
        return 0.0
    sa = set(a)
    sb = set(b)
    inter = sa & sb
    uni = sa | sb
    return len(inter) / len(uni) if uni else 0.0


def parse_date_from_filename(path):
    base = os.path.basename(path)
    m = re.search(r'(20\d{6})', base)
    if m:
        return datetime.strptime(m.group(1), '%Y%m%d').date()
    return None


def article_date_from_row(row, fallback_date=None):
    # yutura CSV 'date' column often empty; use fallback_date if provided
    d = row.get('date', '')
    if isinstance(d, str) and d.strip():
        # Try to parse like '2025年10月2日 16:51'
        m = re.search(r'(20\d{2})\D?(\d{1,2})\D?(\d{1,2})', d)
        if m:
            y,mo,da = map(int, m.groups())
            return datetime(y,mo,da).date()
    return fallback_date


def build_features(trend_csv, yutura_csv, name_candidates_csv=None, out_csv=None):
    df_trend = pd.read_csv(trend_csv)
    df_yu = pd.read_csv(yutura_csv)

    # infer yutura date from filename if rows lack date
    yu_file_date = parse_date_from_filename(yutura_csv)
    if yu_file_date is None:
        yu_file_date = datetime.now().date()

    # prepare yutura rows with tokens and dates
    y_rows = []
    for _, r in df_yu.iterrows():
        title = r.get('title', '')
        art_date = article_date_from_row(r, fallback_date=yu_file_date)
        toks = tokenize(title)
        y_rows.append({'title': title, 'tokens': toks, 'date': art_date})

    # load name candidates if provided to help channel matching
    name_candidates = set()
    if name_candidates_csv and os.path.exists(name_candidates_csv):
        dnc = pd.read_csv(name_candidates_csv)
        for _, r in dnc.iterrows():
            c = r.get('candidate')
            if isinstance(c, str) and c.strip():
                name_candidates.add(c.strip())

    out_rows = []

    for _, v in df_trend.iterrows():
        vid = v.get('videoId')
        vtitle = v.get('title','')
        vchannel = v.get('channelTitle','')
        snap = v.get('snapshot_at_utc')
        try:
            snap_date = datetime.fromisoformat(snap.replace('Z','+00:00')).date()
        except Exception:
            snap_date = datetime.now().date()

        vtoks = tokenize(vtitle)

        for window in (3,7):
            thr = 0.25
            cnt = 0
            max_j = 0.0
            last_date = None
            for yr in y_rows:
                art_date = yr['date'] or yu_file_date
                # include article if within window days before snapshot (0..window)
                if art_date is None:
                    include = True
                else:
                    delta = (snap_date - art_date).days
                    include = (0 <= delta <= window)
                if not include:
                    continue
                j = jaccard(vtoks, yr['tokens'])
                if j >= thr:
                    cnt += 1
                    if (last_date is None) or (yr['date'] and yr['date'] > last_date):
                        last_date = yr['date']
                if j > max_j:
                    max_j = j

            mention_any = 1 if cnt>0 else 0
            # channel matching: substring match in yutura titles or name candidates
            channel_norm = normalize_text(vchannel)
            ch_mentioned = 0
            if channel_norm:
                # check yutura titles
                for yr in y_rows:
                    if channel_norm and channel_norm in normalize_text(yr['title']):
                        ch_mentioned = 1
                        break
                # check name candidates
                if not ch_mentioned and name_candidates:
                    for nc in name_candidates:
                        if nc and nc in channel_norm:
                            ch_mentioned = 1
                            break

            days_since = None
            if last_date is not None and isinstance(last_date, (datetime,)):
                days_since = (snap_date - last_date.date()).days
            elif last_date is not None:
                days_since = (snap_date - last_date).days

            out_rows.append({
                'videoId': vid,
                'snapshot_date': snap_date.isoformat(),
                f'mention_count_{window}d': cnt,
                f'mention_any_{window}d': mention_any,
                f'max_jaccard_{window}d': round(max_j,4),
                f'channel_mentioned_{window}d': ch_mentioned,
                f'days_since_last_mention_{window}d': (days_since if days_since is not None else -1)
            })

    out_df = pd.DataFrame(out_rows)
    # aggregate to one row per videoId: keep snapshot_date from first
    agg = out_df.groupby('videoId').agg({
        'snapshot_date':'first',
        'mention_count_3d':'sum','mention_any_3d':'max','max_jaccard_3d':'max','channel_mentioned_3d':'max','days_since_last_mention_3d':'min',
        'mention_count_7d':'sum','mention_any_7d':'max','max_jaccard_7d':'max','channel_mentioned_7d':'max','days_since_last_mention_7d':'min'
    }).reset_index()

    if out_csv is None:
        out_csv = f"data/features_yutura_{snap_date.isoformat()}.csv"
    os.makedirs(os.path.dirname(out_csv) or '.', exist_ok=True)
    agg.to_csv(out_csv, index=False, encoding='utf-8-sig')
    print(f'Wrote features to {out_csv} rows={len(agg)}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--trend', required=True)
    parser.add_argument('--yutura', required=True)
    parser.add_argument('--name-candidates', default='data/yutura_name_candidates_1-5.csv')
    parser.add_argument('--out', default=None)
    args = parser.parse_args()

    build_features(args.trend, args.yutura, args.name_candidates, args.out)


if __name__ == '__main__':
    main()
