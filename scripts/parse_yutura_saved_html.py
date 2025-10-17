# -*- coding: utf-8 -*-
"""
Parse the saved yutura selenium-rendered HTML and extract titles + links from the "人気のニュース" section.
Saves to data/yutura_news_page5_from_html.csv
"""
from bs4 import BeautifulSoup
import os
import re
import pandas as pd

IN = 'data/yutura_page5_selenium.html'
OUT = 'data/yutura_news_page5_from_html.csv'

with open(IN, 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')

# find the h2/h3 heading that contains "人気のニュース"
rows = []
heading = None
for h in soup.find_all(['h2', 'h3']):
    txt = h.get_text(" ", strip=True)
    if any(k in txt for k in ['人気のニュース', 'YouTuberニュース', '人気ニュース']):
        heading = h
        break

# Determine container: prefer heading-based container, else fall back to known containers
container = None
if heading:
    container = heading.find_parent()
    while container and (container.name != 'body') and ('news-latest' not in (container.get('class') or []) and 'news' not in (container.get('class') or [])):
        container = container.find_parent()

if not container:
    container = soup.select_one('.news-latest') or soup.select_one('section.news') or soup.select_one('#main') or soup

# collect all ul elements with class containing 'news-list' inside the container
uls = container.find_all('ul', class_=re.compile(r'news-list')) if container else soup.select('.news-list')
if not uls:
    uls = soup.select('.news-list')
idx = 1
for ul in uls:
    lis = ul.find_all('li')
    for li in lis:
        title_node = li.find(class_='title')
        a = title_node.find('a') if title_node else li.find('a')
        if not a:
            continue
        title = a.get_text(' ', strip=True)
        if not title:
            title = a.get('aria-label') or a.get('title') or ''
        href = a.get('href') or ''
        if href and href.startswith('/'):
            href = 'https://yutura.net' + href
        date_tag = li.find('p', class_='date')
        date_text = date_tag.get_text(strip=True) if date_tag else ''
        rows.append({'rank': idx, 'title': title, 'url': href, 'date': date_text})
        idx += 1

if rows:
    os.makedirs('data', exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT, index=False, encoding='utf-8-sig')
    print(f'saved {OUT} rows={len(rows)}')
else:
    print('no rows found')
