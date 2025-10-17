#!/usr/bin/env python3
"""
Render and parse multiple pages from yutura.net news listing using Selenium.

Usage example:
  python scripts/scrape_yutura_pages_selenium.py --start 1 --end 5 --out data/yutura_news_pages_1-5.csv

This script will visit each page, wait for rendering, extract all news items (handles ad-split lists),
and save a combined CSV with columns: rank,page,title,url,date,source_page.
"""
import argparse
import logging
import os
import random
import time
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


BASE_URL = "https://yutura.net/news/page/{page}"


def parse_page_html(html, base_url="https://yutura.net"):
    soup = BeautifulSoup(html, "html.parser")

    # Try to find the specific "人気のニュース" heading first
    header = soup.find(lambda tag: tag.name in ["h2", "h3"] and "人気のニュース" in tag.get_text())
    container = None
    if header:
        # The news lists are commonly the next sibling section/div
        container = header.find_next_sibling()

    if container is None:
        # Fallbacks: common classes/sections observed on the site
        container = soup.find("section", class_="news-latest") or soup.find("div", class_="news-latest")

    if container is None:
        # As last resort parse entire document
        container = soup

    # Collect all ul elements that have 'news-list' in their class (handles ad-split lists)
    uls = []
    for ul in container.find_all("ul"):
        classes = ul.get("class") or []
        if any("news-list" in c for c in classes):
            uls.append(ul)

    # If none found under container, search globally
    if not uls:
        for ul in soup.find_all("ul"):
            classes = ul.get("class") or []
            if any("news-list" in c for c in classes):
                uls.append(ul)

    items = []
    for ul in uls:
        for li in ul.find_all("li"):
            # Title extraction: prefer h3.title a
            a = li.select_one("h3.title a") or li.find("a", href=True)
            if not a:
                continue
            title = a.get("aria-label") or a.get_text(strip=True)
            href = a.get("href")
            url = urljoin(base_url, href) if href else ""

            # Date extraction: common tags
            date_tag = li.find("time") or li.find("span", class_="date") or li.find("small")
            date_text = date_tag.get_text(strip=True) if date_tag else ""

            items.append({"title": title, "url": url, "date": date_text})

    return items


def create_driver(headless=True):
    options = webdriver.ChromeOptions()
    if headless:
        # For modern Chrome, --headless=new is available; fallback to --headless for compatibility
        try:
            options.add_argument("--headless=new")
        except Exception:
            options.add_argument("--headless")
        options.add_argument("--disable-gpu")
    # Common options to reduce detection
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1200,800")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def scrape_pages(start_page, end_page, out_path, headless=True, save_html_dir=None, delay_range=(1.0, 2.5)):
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    if save_html_dir:
        os.makedirs(save_html_dir, exist_ok=True)

    driver = create_driver(headless=headless)
    collected = []
    rank_counter = 1

    try:
        for page in range(start_page, end_page + 1):
            url = BASE_URL.format(page=page)
            logging.info(f"Fetching page {page}: {url}")
            driver.get(url)
            # Wait a bit for JS to render
            time.sleep(2.0)

            html = driver.page_source
            if save_html_dir:
                fname = os.path.join(save_html_dir, f"yutura_page_{page}.html")
                with open(fname, "w", encoding="utf-8") as f:
                    f.write(html)
                logging.info(f"Saved rendered HTML to {fname}")

            items = parse_page_html(html)
            logging.info(f"Parsed {len(items)} items on page {page}")

            for it in items:
                it_record = {
                    "rank": rank_counter,
                    "page": page,
                    "title": it.get("title", ""),
                    "url": it.get("url", ""),
                    "date": it.get("date", ""),
                    "source_page": url,
                }
                collected.append(it_record)
                rank_counter += 1

            # polite delay between pages
            time.sleep(random.uniform(*delay_range))

    finally:
        try:
            driver.quit()
        except Exception:
            pass

    if collected:
        df = pd.DataFrame(collected)
        df.to_csv(out_path, index=False, encoding="utf-8-sig")
        logging.info(f"Wrote {len(df)} rows to {out_path}")
    else:
        logging.warning("No items collected; no CSV written")


def main():
    parser = argparse.ArgumentParser(description="Scrape multiple yutura.net news pages via Selenium and save CSV")
    parser.add_argument("--start", type=int, default=1, help="start page (inclusive)")
    parser.add_argument("--end", type=int, default=1, help="end page (inclusive)")
    parser.add_argument("--out", type=str, default=None, help="output CSV path; default includes date if not provided")
    parser.add_argument("--headless", action="store_true", help="run browser headless")
    parser.add_argument("--save-html-dir", type=str, default=None, help="directory to save rendered HTML per page")
    parser.add_argument("--date-stamp", action="store_true", help="append YYYYMMDD date stamp to output filenames/dirs when defaults are used")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    # Compute default paths with optional date stamp
    from datetime import datetime
    today = datetime.now().strftime('%Y%m%d')

    out = args.out
    save_html_dir = args.save_html_dir
    if out is None:
        out = f"data/yutura_news_pages_{today}_{args.start}-{args.end}.csv" if args.date_stamp else f"data/yutura_news_pages_{args.start}-{args.end}.csv"
    if save_html_dir is None and args.date_stamp:
        save_html_dir = f"data/yutura_pages_html_{today}"

    scrape_pages(args.start, args.end, out, headless=args.headless, save_html_dir=save_html_dir)


if __name__ == "__main__":
    main()
