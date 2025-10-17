# -*- coding: utf-8 -*-
"""
Selenium ベースの yutura.net スクレイパー（/news/page/5 を取得）
- webdriver-manager を使って chromedriver を自動取得
- ヘッドレス Chrome でページをレンダリングして HTML を取得
- BeautifulSoup で解析して CSV に保存

注意: 実行にはローカルに Chrome がインストールされている必要があります。
PowerShell 実行例 (faceenv 等の Python 環境で):
pip install selenium webdriver-manager beautifulsoup4 pandas
python scripts\scrape_yutura_selenium.py --page 5
"""
import time
import argparse
import os
import re
from typing import List
from datetime import datetime
from bs4 import BeautifulSoup
import pandas as pd

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

BASE = "https://yutura.net"

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


def fetch_page_with_selenium(url: str, headless: bool = True, wait_selector: str = 'body') -> str:
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    # set a realistic UA
    chrome_options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    try:
        driver.get(url)
        # wait until body or an article list appears
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, wait_selector)))
        except Exception:
            # still continue
            pass
        time.sleep(1)
        html = driver.page_source
        # save debug HTML
        try:
            os.makedirs('data', exist_ok=True)
            with open(f'data/yutura_page_debug.html', 'w', encoding='utf-8') as f:
                f.write(html)
        except Exception:
            pass
        return html
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def scrape_news_page_selenium(page: int = 5) -> pd.DataFrame:
    url = f"{BASE}/news/page/{page}"
    html = fetch_page_with_selenium(url, headless=True, wait_selector='main')
    soup = BeautifulSoup(html, 'html.parser')
    # Try to specifically extract the "人気のニュース" section: find H2 that contains that text,
    # then find the following UL with class containing "news-list" (observed: <ul class="news-list n1">)
    rows = []
    heading = None
    for h in soup.find_all(['h2', 'h3']):
        txt = h.get_text(" ", strip=True)
        if '人気のニュース' in txt:
            heading = h
            break

    ul = None
    if heading:
        ul = heading.find_next('ul', class_=re.compile(r'news-list'))

    if not ul:
        # fallback: try generic selector
        ul = soup.select_one('.news-list.n1') or soup.select_one('.news-list')

    if not ul:
        # last-resort fallback to previous generic item extraction
        items = soup.select('.news-list li, .news li, article, .post')
    else:
        items = ul.find_all('li')

    rank = 0
    for it in items:
        # in the news-list structure, title is under <p class="title"><a ...>
        p_title = it.find('p', class_='title')
        a = p_title.find('a') if p_title else it.find('a')
        if not a:
            continue
        title = a.get_text(' ', strip=True)
        href = a.get('href') or ''
        if href and not href.startswith('http'):
            href = BASE + href
        date_tag = it.find('p', class_='date') or it.find(string=re.compile(r"\d{4}\.\d{2}\.\d{2}|20\d{2}年\d{1,2}月\d{1,2}日"))
        date_text = str(date_tag.get_text(strip=True)) if hasattr(date_tag, 'get_text') else (str(date_tag) if date_tag else '')
        rank += 1
        rows.append({
            'page': page,
            'rank': rank,
            'title': title,
            'url': href,
            'date_hint': date_text,
            'names_guess': guess_names_from_title(title),
        })

    return pd.DataFrame(rows)


def scrape_news_page_selenium_elements(page: int = 5, headless: bool = True) -> pd.DataFrame:
    """Use Selenium to find elements directly and read their .text and href attributes.
    This often yields rendered text (better for JS-heavy or complex DOM).
    """
    url = f"{BASE}/news/page/{page}"
    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    try:
        driver.get(url)
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, '.news-list.n1')))
        except Exception:
            # fallback wait for main
            WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'main')))
        time.sleep(0.8)

        # Save rendered HTML for debugging
        try:
            html = driver.page_source
            os.makedirs('data', exist_ok=True)
            with open(f'data/yutura_page{page}_selenium.html', 'w', encoding='utf-8') as f:
                f.write(html)
        except Exception:
            pass

        # Use h3.title a as observed in the rendered HTML
        elems = driver.find_elements(By.CSS_SELECTOR, '.news-list.n1 li h3.title a')
        if not elems:
            elems = driver.find_elements(By.CSS_SELECTOR, '.news-list li h3.title a')
        rows = []
        print(f"DEBUG: found {len(elems)} elements via CSS selector")
        for i, el in enumerate(elems, start=1):
            # prefer rendered innerText/textContent if .text is empty
            text = (el.text or '').strip()
            if not text:
                text = (el.get_attribute('innerText') or '').strip()
            if not text:
                text = (el.get_attribute('textContent') or '').strip()
            href = el.get_attribute('href') or el.get_attribute('data-href') or ''
            if href and href.startswith('/'):
                href = BASE + href
            print(f"DEBUG: elem[{i}] title_len={len(text)} href={href}")
            rows.append({
                'page': page,
                'rank': i,
                'title': text,
                'url': href,
                'names_guess': guess_names_from_title(text),
            })
        return pd.DataFrame(rows)
    finally:
        try:
            driver.quit()
        except Exception:
            pass


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--page', type=int, default=5)
    args = p.parse_args()
    try:
        # Prefer element-based extraction (more robust for rendered content)
        df = scrape_news_page_selenium_elements(args.page)
        if df.empty:
            df = scrape_news_page_selenium(args.page)
        if not df.empty:
            out_dir = 'data'
            os.makedirs(out_dir, exist_ok=True)
            out_path = os.path.join(out_dir, f'yutura_news_page{args.page}_selenium.csv')
            df.to_csv(out_path, index=False, encoding='utf-8-sig')
            print(f'saved: {out_path} rows={len(df)}')
        else:
            print('no items found on page')
    except Exception as e:
        import traceback
        print('ERROR during selenium scrape:')
        traceback.print_exc()
        raise
