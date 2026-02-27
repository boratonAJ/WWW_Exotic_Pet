"""Scrape Quora search results for mentions of exotic pets.

This is a best-effort scraper using requests + BeautifulSoup. Quora is
JavaScript-heavy and may block or return limited content; for robust
results consider using Selenium or an API.

Output: CSV `WWF_Quora_Crawl_Data.csv` with fields matching Stage 1 Top-20.
"""
import os
import time
import csv
import runpy
from datetime import datetime
from urllib.parse import urljoin, quote_plus

import requests
from bs4 import BeautifulSoup
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Load .env if present
runpy.run_path(os.path.join(os.path.dirname(__file__), 'load_env.py'))

API_KEY = os.environ.get('SERPAPI_KEY')  # not used here but kept for parity

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (compatible; Bot/1.0; +https://example.com/bot)'
}

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

analyzer = SentimentIntensityAnalyzer()


def quora_search_urls(query, max_pages=1):
    """Return a list of Quora question URLs for the given query.

    Note: Quora search pagination and markup may vary; this function
    parses the server-side HTML returned by the /search endpoint.
    """
    urls = []
    base = 'https://www.quora.com'
    q = quote_plus(query)
    for page in range(1, max_pages + 1):
        search_url = f"{base}/search?q={q}&page={page}"
        resp = requests.get(search_url, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            break
        soup = BeautifulSoup(resp.text, 'html.parser')
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Skip profile and static assets
            if href.startswith('/') and not any(x in href for x in ['/profile/', '/topic/']):
                # normalize
                full = urljoin(base, href.split('?')[0])
                if full not in urls:
                    urls.append(full)
        time.sleep(1)
    return urls


def parse_quora_page(url):
    """Fetch and extract text content from a Quora question/answer page.

    Returns a list of text items (question, answers, comments where available).
    """
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
    except Exception:
        return []
    if resp.status_code != 200:
        return []
    soup = BeautifulSoup(resp.text, 'html.parser')
    texts = []
    # Question title
    title = None
    if soup.title:
        title = soup.title.get_text(separator=' ', strip=True)
    if title:
        texts.append(title)

    # Collect text from common paragraph tags
    for p in soup.find_all('p'):
        t = p.get_text(separator=' ', strip=True)
        if t:
            texts.append(t)

    # Also collect answer blocks heuristically
    for div in soup.find_all('div'):
        classes = ' '.join(div.get('class') or [])
        if 'Answer' in classes or 'answer' in classes.lower() or 'answer_text' in classes:
            t = div.get_text(separator=' ', strip=True)
            if t:
                texts.append(t)

    # Deduplicate and return
    seen = set()
    out = []
    for t in texts:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def map_category_from_text(text):
    low = text.lower()
    for cat, slist in species_to_categories.items():
        for sp in slist:
            if sp in low:
                return cat
    return 'Other'


def crawl_quora(species_list, max_pages=1):
    rows = []
    for species in species_list:
        query = f"pet {species} ownership"
        urls = quora_search_urls(query, max_pages=max_pages)
        for url in urls:
            items = parse_quora_page(url)
            for item in items:
                combined = item.lower()
                matched_qs = [q for q, kws in question_map.items() if any(k in combined for k in kws)]
                rows.append({
                    'platform': 'Quora',
                    'text_content': item,
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'keyword_used': f'pet {species}',
                    'category': map_category_from_text(item),
                    'source_url': url,
                    'country_context': 'Unknown',
                    'location_geographic': 'Unknown',
                    'sentiment_score': analyzer.polarity_scores(item)['compound'],
                    'top_20_mapping': ', '.join(matched_qs)
                })
            time.sleep(1)
    return rows


def save_csv(rows, path='WWF_Quora_Crawl_Data.csv'):
    if not rows:
        print('No rows to save')
        return
    keys = rows[0].keys()
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
    print(f'Saved {len(rows)} rows to {path}')


if __name__ == '__main__':
    # flatten species list
    search_species = [s for sl in species_to_categories.values() for s in sl]
    rows = crawl_quora(search_species, max_pages=1)
    save_csv(rows)
