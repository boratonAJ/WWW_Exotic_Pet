import time
import pandas as pd
from serpapi import Client
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime

import os
import runpy
# Load .env helper to populate environment variables (if .env exists)
runpy.run_path(os.path.join(os.path.dirname(__file__), '..', 'scripts', 'load_env.py'))
API_KEY = os.environ.get('SERPAPI_KEY')
if not API_KEY:
    raise RuntimeError('SERPAPI_KEY environment variable not set; copy .env.example to .env')
client = Client(api_key=API_KEY)
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

search_species = [s for sl in species_to_categories.values() for s in sl]

all_data = []

for species in search_species:
    print(f"Searching: {species}")
    params = {
        "q": f"pet {species} ownership",
        "engine": "google",
        "location": "United States",
        "hl": "en",
        "gl": "us",
        "api_key": API_KEY
    }
    try:
        resp = client.search(params)
        results = resp.as_dict()
        if not results or 'organic_results' not in results:
            print(f" -> no organic results for {species}")
            time.sleep(1)
            continue
        for item in results.get('organic_results', []):
            snippet = (item.get('snippet') or '').lower()
            title = (item.get('title') or '').lower()
            combined_text = title + ' ' + snippet
            matched_qs = [q for q, kws in question_map.items() if any(k in combined_text for k in kws)]
            all_data.append({
                'platform': 'Google Search',
                'text_content': combined_text,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'keyword_used': f'pet {species}',
                'category': next((cat for cat, sl in species_to_categories.items() if species in sl), 'Other'),
                'source_url': item.get('link'),
                'country_context': 'United States',
                'location_geographic': 'National (US)',
                'sentiment_score': analyzer.polarity_scores(combined_text)['compound'],
                'top_20_mapping': ', '.join(matched_qs)
            })
        time.sleep(1)
    except Exception as e:
        print(' -> exception:', e)
        time.sleep(1)

if all_data:
    df = pd.DataFrame(all_data)
    df.to_csv('WWF_Google_Crawl_Data.csv', index=False)
    print(f"Saved {len(df)} rows to WWF_Google_Crawl_Data.csv")
else:
    print('No data collected')
