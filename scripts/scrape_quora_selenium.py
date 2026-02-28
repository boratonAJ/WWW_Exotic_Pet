"""Selenium fallback for scraping Quora pages when requests-based scraping is insufficient.

This script uses Selenium + webdriver-manager to launch a headless Chrome browser,
navigate to Quora question pages, and extract question and answer text reliably.

Notes:
- Requires Chrome (or Chromium) to be installed on the machine running the script.
- Install dependencies: `pip install selenium webdriver-manager beautifulsoup4 python-dotenv`.
"""
import os
import time
import csv
import runpy
from datetime import datetime
from urllib.parse import urljoin

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Load .env if present
runpy.run_path(os.path.join(os.path.dirname(__file__), 'load_env.py'))

analyzer = SentimentIntensityAnalyzer()

def get_driver(headless=True):
    opts = Options()
    if headless:
        opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    installed_path = ChromeDriverManager().install()
    # webdriver-manager may return a metadata file path; walk the parent folder to find the actual
    # chromedriver binary. This is more robust across platform/zip layouts.
    exe_path = None
    base_dir = installed_path if os.path.isdir(installed_path) else os.path.dirname(installed_path)
    for root, dirs, files in os.walk(base_dir):
        if 'chromedriver' in files:
            exe_path = os.path.join(root, 'chromedriver')
            break
    if exe_path is None:
        # fallback to the installed_path itself
        exe_path = installed_path
    # ensure executable bit
    try:
        if os.path.isfile(exe_path):
            os.chmod(exe_path, os.stat(exe_path).st_mode | 0o111)
    except Exception:
        pass
    service = Service(exe_path)
    driver = webdriver.Chrome(service=service, options=opts)
    return driver


def selenium_parse_page(url, driver):
    driver.get(url)
    time.sleep(2)  # give JS some time to load
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    texts = []
    if soup.title:
        texts.append(soup.title.get_text(separator=' ', strip=True))
    for p in soup.find_all('p'):
        t = p.get_text(separator=' ', strip=True)
        if t:
            texts.append(t)
    # heuristics for answer containers
    for div in soup.find_all('div'):
        classes = ' '.join(div.get('class') or [])
        if 'Answer' in classes or 'answer' in classes.lower() or 'answer_text' in classes:
            t = div.get_text(separator=' ', strip=True)
            if t:
                texts.append(t)
    # dedupe
    out = []
    seen = set()
    for t in texts:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def main(urls, output='WWF_Quora_Crawl_Selenium.csv'):
    driver = get_driver(headless=True)
    rows = []
    for url in urls:
        print('Fetching', url)
        try:
            items = selenium_parse_page(url, driver)
            for item in items:
                rows.append({
                    'platform': 'Quora',
                    'text_content': item,
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'keyword_used': '',
                    'category': '',
                    'source_url': url,
                    'country_context': 'Unknown',
                    'location_geographic': 'Unknown',
                    'sentiment_score': analyzer.polarity_scores(item)['compound'],
                    'top_20_mapping': ''
                })
        except Exception as e:
            print('error', e)
        time.sleep(1)
    driver.quit()
    if rows:
        keys = rows[0].keys()
        with open(output, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
        print('Saved', len(rows), 'rows to', output)
    else:
        print('No rows collected')


if __name__ == '__main__':
    # Example usage: define a small set of Quora URLs to fetch
    sample_urls = [
        'https://www.quora.com/Can-you-keep-a-monkey-as-a-pet',
    ]
    main(sample_urls)
