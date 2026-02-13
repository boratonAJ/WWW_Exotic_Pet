"""
Data processing script.

Run this script to process raw data into processed data.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils import load_config


def main():
    """Main processing function."""
    # Load configuration
    config = load_config('configs/default.yaml')
    
    print("Configuration loaded:")
    print(config)
    
    # Add your data processing logic here


if __name__ == '__main__':
    main()


import praw
import pandas as pd
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# 1. AUTHENTICATION
reddit = praw.Reddit(
    client_id='YOUR_ID', 
    client_secret='YOUR_SECRET', 
    user_agent='WWF_Team5_Scraper'
)

# 2. KEYWORD MAPPING (Aligning to Category Field)
# Grouping species into the high-risk categories defined in Q8
category_map = {
    "Primate": ["monkey", "macaque", "chimpanzee", "slow loris"],
    "Big Cat": ["tiger", "lion", "serval", "caracal", "cheetah"],
    "Reptile": ["python", "boa", "cobra", "iguana", "monitor lizard"],
    "Bird": ["parrot", "macaw", "cockatoo"]
}

# 3. TOP 20 QUESTIONS MAPPING (For filtering and analysis)
question_map = {
    "Q1_Sentiment": ["love", "want", "dangerous", "cruel", "cool", "illegal"],
    "Q4_Legal_Risk": ["illegal", "banned", "permit", "law", "license"],
    "Q5_Safety_Risk": ["attack", "bite", "venom", "danger", "kill"],
    "Q6_Animal_Welfare": ["cruelty", "suffering", "captivity", "care"],
    "Q16_Knowledge_Gaps": ["didn't know", "unaware", "confused", "misconception"]
}

def scrape_exotic_pet_data(target_keywords):
    results = []
    analyzer = SentimentIntensityAnalyzer()

    for keyword in target_keywords:
        # Searching public discussions
        for submission in reddit.subreddit("all").search(keyword, limit=500):
            text = (submission.title + " " + submission.selftext).lower()
            
            # Determine Category (Q8)
            category = "Other"
            for cat, species_list in category_map.items():
                if any(s in text for s in species_list):
                    category = cat
                    break

            # Data Record with Expected Fields
            results.append({
                "platform": "Reddit", # Field: platform
                "text_content": text, # Field: text_content
                "date": datetime.fromtimestamp(submission.created_utc).strftime('%Y-%m-%d'), # Field: date
                "keyword_used": keyword, # Field: keyword_used
                "category": category, # Field: category
                "source_url": f"https://www.reddit.com{submission.permalink}", # Field: source_url
                "country_context": "United States", # Project Scope
                "location_geographic": submission.subreddit.display_name, # Proxy for location context
                "sentiment_score": analyzer.polarity_scores(text)['compound'], # Q1
                "questions_mapped": [q for q, kws in question_map.items() if any(k in text for k in kws)]
            })
            
    return pd.DataFrame(results)

# 4. EXECUTION
# Combining species-level keywords for Q9
all_species = [s for sublist in category_map.values() for s in sublist]
df = scrape_exotic_pet_data(all_species)
df.to_csv("WWF_Expected_Fields_Dataset.csv", index=False)