#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
extract_top50_titles.py
-----------------------
trending_JP_20250926.csv などのトレンドCSVから先頭50件の videoId/title/channelTitle/viewCount/snapshot_at_utc を抽出して CSV に保存します。

使い方:
  python scripts/extract_top50_titles.py 

出力:
  yt_trend/trending_titles_50.csv
"""
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IN_CSV = ROOT / "trending_JP_20250926.csv"
OUT_DIR = ROOT / "yt_trend"
OUT_CSV = OUT_DIR / "trending_titles_50.csv"

def extract_top50(in_csv: Path, out_csv: Path, n: int = 50):
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with in_csv.open("r", encoding="utf-8") as inf, out_csv.open("w", encoding="utf-8", newline="") as outf:
        reader = csv.DictReader(inf)
        fieldnames = ["snapshot_at_utc", "videoId", "title", "channelTitle", "viewCount"]
        writer = csv.DictWriter(outf, fieldnames=fieldnames)
        writer.writeheader()
        for i, row in enumerate(reader):
            if i >= n:
                break
            writer.writerow({k: row.get(k, "") for k in fieldnames})
    print(f"Saved {n} rows to: {out_csv}")

if __name__ == '__main__':
    if not IN_CSV.exists():
        print(f"Input CSV not found: {IN_CSV}")
    else:
        extract_top50(IN_CSV, OUT_CSV, 50)
