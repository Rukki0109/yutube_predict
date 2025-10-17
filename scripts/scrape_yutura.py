# -*- coding: utf-8 -*-
"""
Scrape yutura.net news page (example: /news/page/5) and extract titles and guessed names.
Saves CSV to data/yutura_news_page5.csv
"""
import time
import re
import random
from datetime import datetime
from typing import List
import requests
from bs4 import BeautifulSoup
import pandas as pd

BASE = "https://yutura.net"
HEADERS = {
    # Use a realistic modern Chrome UA to reduce chance of simple bot blocking
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://yutura.net/",
}
SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def get(url, sleep=(0.8, 1.6), timeout=15):
    time.sleep(random.uniform(*sleep))
    last_exc = None
    for i in range(3):
        try:
            r = SESSION.get(url, timeout=timeout)
        except Exception as e:
            last_exc = e
            print(f"GET attempt {i+1} exception for {url}: {e}")
            time.sleep(1.5 * (i + 1))
            continue
        if r.status_code == 200:
            return r
        # log non-200
        print(f"GET attempt {i+1} returned status={r.status_code} for {url}")
        # short backoff
        time.sleep(1.5 * (i + 1))
    # if we reach here, raise a helpful error
    if last_exc:
        raise last_exc
    raise RuntimeError(f"Failed to GET {url} after retries; last status={r.status_code}")


JA_PUNCT = "！!？?（）()「」『』【】・、。［］[]"

def normalize_txt(s: str) -> str:
    s = s or ""
    s = re.sub(rf"[{JA_PUNCT}]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def guess_names_from_title(title: str) -> List[str]:
    t = normalize_txt(title)
    cands = re.findall(r"[ァ-ヴーA-Za-z0-9][ァ-ヴーA-Za-z0-9・\-]{1,}", t)
    uniq = []
    for w in cands:
        if w not in uniq:
            uniq.append(w)
    return uniq[:8]


def scrape_news_page(page: int = 5) -> pd.DataFrame:
    url = f"{BASE}/news/page/{page}"
    print(f"GET {url}")
    res = get(url)
    soup = BeautifulSoup(res.text, "html.parser")

    rows = []
    # Find article list items - try common selectors
    items = soup.select(".news-list li, .news li, article, .post")
    if not items:
        # Fallback: find links under main
        items = soup.select("main a")
    rank = 0
    for it in items:
        a = it.find("a")
        if not a:
            continue
        title = a.get_text(" ", strip=True)
        href = a.get("href") or ""
        if href and not href.startswith("http"):
            href = BASE + href
        # try to find date inside item
        date_text = ""
        date_tag = it.find(string=re.compile(r"\d{4}\.\d{2}\.\d{2}|20\d{2}年\d{1,2}月\d{1,2}日"))
        if date_tag:
            date_text = str(date_tag)
        rank += 1
        rows.append({
            "page": page,
            "rank": rank,
            "title": title,
            "url": href,
            "date_hint": date_text,
            "names_guess": guess_names_from_title(title),
        })
    return pd.DataFrame(rows)


if __name__ == '__main__':
    try:
        df = scrape_news_page(5)
        if not df.empty:
            out_dir = "data"
            import os
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, "yutura_news_page5.csv")
            df.to_csv(out_path, index=False, encoding="utf-8-sig")
            print(f"saved: {out_path} rows={len(df)}")
        else:
            print("no items found on page")
    except Exception as e:
        import traceback
        print("ERROR during scrape:")
        traceback.print_exc()
        # fail-fast with non-zero exit so CI / caller can detect
        raise
