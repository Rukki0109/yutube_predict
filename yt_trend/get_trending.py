#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
get_trending.py
----------------
日本の YouTube 急上昇（Trending）一覧を取得して CSV に保存します。

使い方:
  export YT_API_KEY="YOUR_API_KEY"
  python get_trending.py --region JP --max 200 --out trending_YYYYMMDD.csv

備考:
- YouTube Data API v3 の videos.list (chart=mostPopular) を使用。
- 1回の実行でのスナップショットを保存します。日次で回すことで時系列データが作れます。
"""
import os
import sys
import re
from pathlib import Path
# Ensure repository root (parent of yt_trend) is on sys.path so `yt_trendlab` can be imported
ROOT = Path(__file__).resolve().parents[1]
repo_root = str(ROOT)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
try:
    from yt_trendlab import config as yt_config
except Exception:
    yt_config = None
import argparse
import datetime as dt
import pandas as pd
from googleapiclient.discovery import build

def fetch_trending(api_key: str, region_code: str="JP", max_results: int=200):
    # Deprecated simple fetcher; use fetch_trending_advanced instead.
    return fetch_trending_advanced(api_key, region_code=region_code, max_results=max_results)


def fetch_trending_with_category(api_key: str, region_code: str="JP", category_id: str=None, max_results: int=200):
    """
    指定したカテゴリIDでトレンドを取得します。category_id を None にするとカテゴリ指定なしと同等です。

    Parameters
    - api_key: YouTube API key
    - region_code: 2-letter region code (default: JP)
    - category_id: videoCategoryId として渡すカテゴリID文字列（例: '10' = 音楽）
    - max_results: 取得上限（内部でページング）
    """
    youtube = build("youtube", "v3", developerKey=api_key)
    items_all = []
    page_token = None
    remain = max_results
    while remain > 0:
        batch = min(50, remain)
        # videoCategoryId を条件に付けられるようにする
        req_kwargs = dict(
            part="snippet,statistics,contentDetails",
            chart="mostPopular",
            regionCode=region_code,
            maxResults=batch,
            pageToken=page_token
        )
        if category_id:
            req_kwargs["videoCategoryId"] = category_id

        req = youtube.videos().list(**req_kwargs)
        res = req.execute()
        items = res.get("items", [])
        items_all.extend(items)
        page_token = res.get("nextPageToken")
        if not page_token:
            break
        remain -= batch

    rows = []
    ts = dt.datetime.utcnow().isoformat() + "Z"
    for it in items_all:
        snip = it.get("snippet", {})
        stats = it.get("statistics", {})
        cont  = it.get("contentDetails", {})
        rows.append({
            "snapshot_at_utc": ts,
            "videoId": it.get("id"),
            "title": snip.get("title"),
            "description": snip.get("description"),
            "channelId": snip.get("channelId"),
            "channelTitle": snip.get("channelTitle"),
            "publishedAt": snip.get("publishedAt"),
            "categoryId": snip.get("categoryId"),
            "tags": "|".join(snip.get("tags", [])) if snip.get("tags") else "",
            "thumbnail": snip.get("thumbnails", {}).get("high", {}).get("url"),
            "viewCount": int(stats.get("viewCount", 0)) if stats.get("viewCount") is not None else None,
            "likeCount": int(stats.get("likeCount", 0)) if stats.get("likeCount") is not None else None,
            "commentCount": int(stats.get("commentCount", 0)) if stats.get("commentCount") is not None else None,
            "duration": cont.get("duration")
        })
    return pd.DataFrame(rows)


def iso8601_to_seconds(iso_duration: str) -> int:
    """簡易 ISO8601 期間パーサー（PT#M#S など）を秒に変換"""
    if not iso_duration or not isinstance(iso_duration, str):
        return 0
    # 例: PT1M23S, PT15S, PT2M
    m_s = re.search(r"(\d+)S", iso_duration)
    m_m = re.search(r"(\d+)M", iso_duration)
    secs = 0
    if m_m:
        secs += int(m_m.group(1)) * 60
    if m_s:
        secs += int(m_s.group(1))
    return secs


def is_shorts_like(title: str, description: str, duration_seconds: int) -> bool:
    txt = ((title or "") + " " + (description or "")).lower()
    if '#shorts' in txt or ' #shorts' in txt:
        return True
    # duration threshold: <= 60 sec
    try:
        if duration_seconds is not None and int(duration_seconds) <= 60:
            return True
    except Exception:
        pass
    return False


def fetch_trending_advanced(api_key: str, region_code: str = "JP", max_results: int = 200, category_id: str = None, exclude_shorts: bool = False):
    """mostPopular をページングで取得し、オプションで Shorts を除外して返す。
    戻り値は rows のリスト（後で DataFrame に変換）
    """
    youtube = build("youtube", "v3", developerKey=api_key)
    results = []

    fetched = 0
    page_token = None
    while fetched < max_results:
        batch = min(50, max_results - fetched)
        kwargs = dict(
            part="id,snippet,contentDetails,statistics",
            chart="mostPopular",
            regionCode=region_code,
            maxResults=batch,
            pageToken=page_token
        )
        if category_id:
            kwargs['videoCategoryId'] = category_id
        req = youtube.videos().list(**kwargs)
        res = req.execute()
        items = res.get('items', [])
        for rank_offset, it in enumerate(items, start=1 + fetched):
            vid = it.get('id')
            snip = it.get('snippet', {})
            stats = it.get('statistics', {})
            cont = it.get('contentDetails', {})

            duration_iso = cont.get('duration', 'PT0S')
            duration_sec = iso8601_to_seconds(duration_iso)
            title = snip.get('title', '')
            desc = snip.get('description', '')

            if exclude_shorts and is_shorts_like(title, desc, duration_sec):
                # mark as excluded (not appended)
                continue

            results.append({
                'snapshot_at_utc': dt.datetime.utcnow().isoformat() + 'Z',
                'rank': rank_offset,
                'videoId': vid,
                'title': title,
                'description': desc,
                'channelId': snip.get('channelId'),
                'channelTitle': snip.get('channelTitle'),
                'publishedAt': snip.get('publishedAt'),
                'categoryId': snip.get('categoryId'),
                'tags': '|'.join(snip.get('tags', [])) if snip.get('tags') else '',
                'thumbnail': snip.get('thumbnails', {}).get('high', {}).get('url'),
                'viewCount': int(stats.get('viewCount')) if stats.get('viewCount') is not None else None,
                'likeCount': int(stats.get('likeCount')) if stats.get('likeCount') is not None else None,
                'commentCount': int(stats.get('commentCount')) if stats.get('commentCount') is not None else None,
                'duration': duration_iso,
                'duration_seconds': duration_sec,
            })

        fetched += len(items)
        page_token = res.get('nextPageToken')
        if not page_token:
            break

    return pd.DataFrame(results)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--region", default="JP")
    parser.add_argument("--category", default=None, help="videoCategoryId を指定するとそのカテゴリのみ取得します（例: 10 = 音楽）")
    parser.add_argument("--exclude-shorts", action='store_true', help="ショート動画（Shorts）と推定されるものを除外します（タイトルに 'shorts' を含むか、duration が短いもの）")
    parser.add_argument("--max", type=int, default=200)
    parser.add_argument("--out", default=None, help="保存先CSV。デフォルトは trending_YYYYMMDD.csv")
    args = parser.parse_args()

    api_key = os.getenv("YT_API_KEY") or os.getenv("API_KEY") or os.getenv("YOUTUBE_API_KEY")
    # fallback to yt_trendlab config
    if not api_key and yt_config and getattr(yt_config, 'API_KEY', None):
        api_key = yt_config.API_KEY
    if not api_key:
        raise RuntimeError("環境変数 YT_API_KEY (または API_KEY / YOUTUBE_API_KEY) を設定するか yt_trendlab.config.API_KEY を設定してください。")

    if args.category:
        df = fetch_trending_with_category(api_key, args.region, args.category, args.max)
    else:
        df = fetch_trending(api_key, args.region, args.max)

    # Exclude shorts if requested (or via config default)
    exclude_shorts = args.exclude_shorts
    if not exclude_shorts and yt_config and getattr(yt_config, 'DEFAULT_EXCLUDE_SHORTS', False):
        exclude_shorts = True
    if exclude_shorts and not df.empty:
        # Heuristic: title contains 'shorts' (case-insensitive) or duration indicates short (<60s)
        def is_shorts(row):
            title = (row.get('title') or '').lower()
            dur = row.get('duration') or ''
            if 'shorts' in title or 'short' in title:
                return True
            # duration is iso8601 like PT15S or PT1M23S
            if isinstance(dur, str) and dur.startswith('PT'):
                # extract seconds roughly
                import re
                m_s = re.search(r"(\d+)S", dur)
                m_m = re.search(r"(\d+)M", dur)
                secs = 0
                if m_m:
                    secs += int(m_m.group(1)) * 60
                if m_s:
                    secs += int(m_s.group(1))
                if secs > 0 and secs <= 60:
                    return True
            return False

        orig_count = len(df)
        df = df[~df.apply(is_shorts, axis=1)].reset_index(drop=True)
        print(f"Excluded shorts: {orig_count - len(df)} videos removed")
    if args.out is None:
        # default out dir from config if available
        out_dir = None
        if yt_config and getattr(yt_config, 'DEFAULT_OUT_DIR', None):
            out_dir = yt_config.DEFAULT_OUT_DIR
        else:
            out_dir = "."
        today = dt.datetime.now().strftime("%Y%m%d")
        args.out = str(Path(out_dir) / f"trending_{args.region}_{today}.csv")
    # Ensure output directory exists
    out_path = Path(args.out)
    if out_path.parent and not out_path.parent.exists():
        out_path.parent.mkdir(parents=True, exist_ok=True)
    # Ensure output directory exists
    out_path = Path(args.out)
    if out_path.parent and not out_path.parent.exists():
        out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(str(out_path), index=False, encoding="utf-8-sig")
    print(f"✅ Saved: {args.out} (rows={len(df)})")

if __name__ == "__main__":
    main()
