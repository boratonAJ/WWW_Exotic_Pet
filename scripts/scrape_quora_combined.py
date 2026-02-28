"""Combined Quora scraper: requests-based with Selenium fallback.

No CLI parsing; configuration (species maps, question map, and search keywords)
is defined in this file. The script will build Quora search URLs like
`https://www.quora.com/search?q=pet+<keyword>` and attempt a requests fetch
and parse. If no results are found for a URL, the script uses Selenium to
render the page and extract text.

Output: WWF_Quora_Crawl_Combined.csv
"""
import os
import time
import csv
import runpy
from datetime import datetime
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Try importing Selenium pieces; only used for fallback
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except Exception:
    SELENIUM_AVAILABLE = False

# Load environment if present
runpy.run_path(os.path.join(os.path.dirname(__file__), 'load_env.py'))

analyzer = SentimentIntensityAnalyzer()

species_to_categories =  {
    "Primate": ["monkey", "macaque", "chimpanzee", "slow loris"],
    "Big Cat": ["tiger", "lion", "serval", "caracal", "cheetah"],
    "Reptile": ["python", "boa", "cobra", "iguana", "monitor lizard"],
    "Bird": ["parrot", "macaw", "cockatoo"]
}

question_map = {
    "Q1_Sentiment": ["love", "want", "dangerous", "cruel", "cool", "illegal"],
    "Q4_Legal_Risk": ["illegal", "banned", "permit", "law", "license"],
    "Q5_Safety_Risk": ["attack", "bite", "venom", "danger", "kill"],
    "Q6_Animal_Welfare": ["cruelty", "suffering", "captivity", "care"],
    "Q16_Knowledge_Gaps": ["didn't know", "unaware", "confused", "misconception"]
}


def build_search_urls(keywords):
    base = 'https://www.quora.com/search?q='
    return [base + quote_plus(k) for k in keywords]


def parse_with_requests(url, session=None):
    s = session or requests.Session()
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/115.0 Safari/537.36'
    }
    try:
        r = s.get(url, headers=headers, timeout=10)
    except Exception:
        return []
    if r.status_code != 200:
        return []
    soup = BeautifulSoup(r.text, 'html.parser')
    texts = []
    # search page: collect question snippets and any visible paragraph text
    for a in soup.find_all('a'):
        text = (a.get_text(separator=' ', strip=True) or '')
        if text and len(text) > 20:
            texts.append(text)
    for p in soup.find_all('p'):
        t = p.get_text(separator=' ', strip=True)
        if t and len(t) > 40:
            texts.append(t)
    # dedupe
    out = []
    seen = set()
    for t in texts:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def get_selenium_driver(headless=True):
    opts = Options()
    if headless:
        # uses modern headless flag if available
        opts.add_argument('--headless=new')
    opts.add_argument('--no-sandbox')
    opts.add_argument('--disable-dev-shm-usage')
    opts.add_argument('--disable-gpu')
    installed_path = ChromeDriverManager().install()
    exe_path = None
    base_dir = installed_path if os.path.isdir(installed_path) else os.path.dirname(installed_path)
    for root, dirs, files in os.walk(base_dir):
        if 'chromedriver' in files:
            exe_path = os.path.join(root, 'chromedriver')
            break
    if exe_path is None:
        exe_path = installed_path
    try:
        if os.path.isfile(exe_path):
            os.chmod(exe_path, os.stat(exe_path).st_mode | 0o111)
    except Exception:
        pass
    service = Service(exe_path)
    driver = webdriver.Chrome(service=service, options=opts)
    return driver


def selenium_fetch(url, driver):
    driver.get(url)
    time.sleep(2)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    texts = []
    for q in soup.find_all('a'):
        t = q.get_text(separator=' ', strip=True)
        if t and len(t) > 20:
            texts.append(t)
    for p in soup.find_all('p'):
        t = p.get_text(separator=' ', strip=True)
        if t and len(t) > 40:
            texts.append(t)
    # also attempt to grab common answer containers
    for div in soup.find_all('div'):
        classes = ' '.join(div.get('class') or [])
        if 'Answer' in classes or 'answer' in classes.lower() or 'answer_text' in classes:
            t = div.get_text(separator=' ', strip=True)
            if t and len(t) > 40:
                texts.append(t)
    out = []
    seen = set()
    for t in texts:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def map_category_and_questions(text):
    text_l = text.lower()
    category = 'Other'
    for cat, species_list in species_to_categories.items():
        if any(s.lower() in text_l for s in species_list):
            category = cat
            break
    mapped_qs = [q for q, kws in question_map.items() if any(k.lower() in text_l for k in kws)]
    return category, mapped_qs


def collect_for_keywords(keywords, output='WWF_Quora_Crawl_Combined.csv'):
    search_urls = build_search_urls(keywords)
    session = requests.Session()
    rows = []
    selenium_driver = None
    for kw, url in zip(keywords, search_urls):
        print('Processing', kw)
        items = parse_with_requests(url, session=session)
        if not items and SELENIUM_AVAILABLE:
            if selenium_driver is None:
                selenium_driver = get_selenium_driver(headless=True)
            items = selenium_fetch(url, selenium_driver)
        for it in items:
            cat, mapped_qs = map_category_and_questions(it)
            rows.append({
                'platform': 'Quora',
                'text_content': it,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'keyword_used': kw,
                'category': cat,
                'source_url': url,
                'country_context': 'Unknown',
                'location_geographic': 'Unknown',
                'sentiment_score': analyzer.polarity_scores(it)['compound'],
                'top_20_mapping': ', '.join(mapped_qs)
            })
        time.sleep(1)
    if selenium_driver is not None:
        selenium_driver.quit()
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
    # Build a small set of keywords from species_to_categories (first species of each category)
    small_keywords = []
    for cat, sl in species_to_categories.items():
        # use the first species in the list and a friendly phrase
        if sl:
            small_keywords.append(f'pet {sl[0]}')
    # Add a couple of generic keywords
    small_keywords.extend(['pet monkey', 'exotic pet ownership'])
    collect_for_keywords(small_keywords)
