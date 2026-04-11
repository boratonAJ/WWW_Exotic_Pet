import csv
import time
import hashlib
import logging
import re
from datetime import datetime, timezone
from datetime import timedelta
from dataclasses import dataclass, fields
from urllib.parse import unquote, urlparse, parse_qs
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Step 0: Runtime configuration (output naming, pacing, and request limits).
OUTPUT_CSV    = f"wildlife_combined_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
REQUEST_DELAY = 3      # seconds between requests incase you get rate limited
DDG_RESULTS   = 10     # max results per DuckDuckGo query
REDDIT_LIMIT  = 50     # posts per Reddit query
SNIPPET_LIMIT = 400 
SUBCOMMENTS_LIMIT = 20
SUBCOMMENTS_CHAR_LIMIT = 2000
MAX_SUBCOMMENTS_FETCH_PER_QUERY = 15

DATE_END_UTC = datetime.now(timezone.utc)
DATE_START_UTC = DATE_END_UTC - timedelta(days=365 * 5)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# Step 0.4: Seed query banks for search collection.
DDG_QUERIES = [
    "exotic pet for sale no papers",
    "slow loris for sale pet",
    "pangolin for sale available",
    "baby monkey for sale contact",
    "african grey unringed for sale",
    "tortoise for sale no paperwork",
    "tiger cub for sale adopt",
    "kinkajou for sale shipping",
    "chameleon for sale live arrival",
    "exotic reptile discreet shipping",
]

DDG_FALLBACK_QUERIES = [
    "exotic pet for sale",
    "reptile for sale",
]

REDDIT_QUERIES = [
    "exotic pet for sale no papers",
    "pangolin for sale",
    "slow loris pet",
    "African grey unringed sale",
    "reptile live arrival shipping",
    "monkey for sale contact",
]

REDDIT_SUBREDDITS = [
    "r/reptiles",
    "r/parrots",
    "r/exoticpets",
]

# Step 0.5: Define screening vocab for risk and species tagging.
RED_FLAG_TERMS = [
    "no papers", "no cites", "unringed", "no permit",
    "discreet shipping", "live arrival guaranteed",
    "whatsapp", "telegram", "dm for price", "pm for price",
    "no questions asked", "cash only",
]

SPECIES_TERMS = [
    "pangolin", "slow loris", "sun bear", "binturong", "kinkajou",
    "african grey", "hyacinth macaw", "boa constrictor",
    "star tortoise", "ploughshare tortoise", "tiger", "leopard",
    "serval", "caracal", "ocelot", "pygmy marmoset", "capuchin",
]

@dataclass
class Finding:
    source:       str   # "duckduckgo" or "reddit"
    query:        str
    url:          str
    title:        str
    snippet:      str
    red_flags:    str   # comma-separated matched terms
    species_hits: str   # comma-separated matched species
    sub_comments: str   # pipe-separated nested comments (reddit only)
    timestamp:    str
    result_hash:  str

def make_hash(url: str, query: str) -> str:
    # Step 0.1: Build a short stable id used for deduplication.
    return hashlib.md5(f"{url}|{query}".encode()).hexdigest()[:12]


def check_flags(text: str) -> tuple[list[str], list[str]]:
    # Step 0.2: Detect high-risk terms and notable species mentions.
    lower = text.lower()
    flags   = [t for t in RED_FLAG_TERMS if t in lower]
    species = [s for s in SPECIES_TERMS  if s in lower]
    return flags, species


def make_finding(source, query, url, title, snippet, sub_comments: str = "", timestamp: str | None = None) -> Finding:
    # Step 0.3: Normalize raw search result into a single Finding record.
    flags, species = check_flags(f"{title} {snippet}")
    return Finding(
        source       = source,
        query        = query,
        url          = url,
        title        = title[:200],
        snippet      = snippet[:SNIPPET_LIMIT],
        red_flags    = ", ".join(sorted(set(flags))),
        species_hits = ", ".join(sorted(set(species))),
        sub_comments = sub_comments[:SUBCOMMENTS_CHAR_LIMIT],
        timestamp    = timestamp or datetime.now(timezone.utc).isoformat(),
        result_hash  = make_hash(url, query),
    )


def is_within_date_window(created_utc: float) -> bool:
    created_dt = datetime.fromtimestamp(created_utc, tz=timezone.utc)
    return DATE_START_UTC <= created_dt <= DATE_END_UTC


def flatten_reddit_replies(children: list[dict], acc: list[str]) -> None:
    for child in children:
        if child.get("kind") != "t1":
            continue
        data = child.get("data", {})
        body = (data.get("body") or "").strip().replace("\n", " ")
        if body:
            acc.append(body)
        replies = data.get("replies")
        if isinstance(replies, dict):
            reply_children = replies.get("data", {}).get("children", [])
            flatten_reddit_replies(reply_children, acc)


def fetch_reddit_sub_comments(permalink: str) -> str:
    comments_url = f"https://www.reddit.com{permalink}.json"
    params = {"limit": SUBCOMMENTS_LIMIT, "depth": 4, "sort": "new"}
    payload = reddit_get_json(comments_url, params=params)
    if payload is None:
        return ""
    if not isinstance(payload, list) or len(payload) < 2:
        return ""

    comment_listing = payload[1].get("data", {}).get("children", [])
    comments: list[str] = []
    flatten_reddit_replies(comment_listing, comments)
    return " | ".join(comments[:SUBCOMMENTS_LIMIT])


def reddit_get_json(url: str, params: dict | None = None):
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=15)
            if r.status_code == 429:
                retry_after = int(r.headers.get("Retry-After", "3"))
                backoff = retry_after + attempt * 2
                log.warning(f"Reddit rate-limited (429). Retrying in {backoff}s...")
                time.sleep(backoff)
                continue
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt == 2:
                log.warning(f"Reddit request failed after retries: {e}")
            else:
                time.sleep(2 + attempt)
    return None

def search_duckduckgo(query: str) -> list[Finding]:
    """
    Scrapes DuckDuckGo HTML results. No API key required.
    Uses the html.duckduckgo.com endpoint which returns plain HTML.
    """
    # Step 3.1: Submit query to DDG and parse HTML results.
    url = "https://html.duckduckgo.com/html/"

    def parse_ddg_html(html: str) -> list[Finding]:
        soup = BeautifulSoup(html, "html.parser")
        parsed: list[Finding] = []
        seen_urls: set[str] = set()
        result_links = soup.select(".result__title a, a.result__a")

        for a_tag in result_links[: DDG_RESULTS * 2]:
            title = a_tag.get_text(strip=True)
            href = a_tag.get("href", "")

            # DDG wraps destination URLs.
            if "uddg=" in href:
                qs = parse_qs(urlparse(href).query)
                href = unquote(qs.get("uddg", [href])[0])

            if not href or href in seen_urls:
                continue

            result_node = a_tag.find_parent(class_="result")
            snip = result_node.select_one(".result__snippet") if result_node else None
            snippet = snip.get_text(strip=True) if snip else ""

            seen_urls.add(href)
            parsed.append(make_finding("duckduckgo", query, href, title, snippet))
            if len(parsed) >= DDG_RESULTS:
                break

        return parsed

    def relax_query(q: str) -> str:
        q = re.sub(r"site:\S+", " ", q, flags=re.IGNORECASE)
        q = q.replace('"', " ").replace(" OR ", " ")
        return " ".join(q.split())

    candidate_queries = [query]
    relaxed = relax_query(query)
    if relaxed and relaxed != query:
        candidate_queries.append(relaxed)

    results: list[Finding] = []
    for candidate in candidate_queries:
        for method in ("post", "get"):
            try:
                if method == "post":
                    r = requests.post(url, data={"q": candidate}, headers=HEADERS, timeout=15)
                else:
                    r = requests.get(url, params={"q": candidate}, headers=HEADERS, timeout=15)
                r.raise_for_status()
            except Exception as e:
                log.warning(f"DDG request failed: {e}")
                continue

            results = parse_ddg_html(r.text)
            if results:
                if candidate != query:
                    log.info(f"  DDG fallback query used: {candidate}")
                break

        if results:
            break

    log.info(f"  DDG '{query[:55]}' → {len(results)} results")
    return results

def search_reddit(query: str) -> list[Finding]:
    """
    Uses Reddit's public search JSON endpoint.
    No authentication required for read-only queries.
    """
    # Step 4.1: Query Reddit global search endpoint.
    url = "https://www.reddit.com/search.json"
    params = {"q": query, "sort": "new", "limit": REDDIT_LIMIT, "type": "link", "t": "all"}
    payload = reddit_get_json(url, params=params)
    if payload is None:
        return []
    posts = payload.get("data", {}).get("children", [])

    results = []
    subcomment_fetches = 0
    # Step 4.2: Normalize Reddit posts to Finding rows.
    for post in posts:
        d = post.get("data", {})
        created_utc = float(d.get("created_utc", 0) or 0)
        if created_utc and not is_within_date_window(created_utc):
            continue
        permalink = d.get("permalink", "")
        sub_comments = ""
        if permalink and subcomment_fetches < MAX_SUBCOMMENTS_FETCH_PER_QUERY:
            sub_comments = fetch_reddit_sub_comments(permalink)
            subcomment_fetches += 1
        results.append(make_finding(
            "reddit", query,
            "https://reddit.com" + permalink,
            d.get("title", ""),
            d.get("selftext", "")[:SNIPPET_LIMIT],
            sub_comments=sub_comments,
            timestamp=datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat() if created_utc else None,
        ))

    log.info(f"  Reddit '{query[:55]}' → {len(results)} results")
    return results


def search_reddit_subreddit(subreddit: str, query: str) -> list[Finding]:
    """Search within a specific subreddit using the public JSON API."""
    # Step 5.1: Query one subreddit at a time with the same normalization path.
    url = f"https://www.reddit.com/{subreddit}/search.json"
    params = {"q": query, "restrict_sr": "on", "limit": REDDIT_LIMIT, "sort": "new", "t": "all"}
    payload = reddit_get_json(url, params=params)
    if payload is None:
        return []
    posts = payload.get("data", {}).get("children", [])

    results = []
    subcomment_fetches = 0
    for post in posts:
        d = post.get("data", {})
        created_utc = float(d.get("created_utc", 0) or 0)
        if created_utc and not is_within_date_window(created_utc):
            continue
        permalink = d.get("permalink", "")
        sub_comments = ""
        if permalink and subcomment_fetches < MAX_SUBCOMMENTS_FETCH_PER_QUERY:
            sub_comments = fetch_reddit_sub_comments(permalink)
            subcomment_fetches += 1
        results.append(make_finding(
            "reddit", f"{subreddit}: {query}",
            "https://reddit.com" + permalink,
            d.get("title", ""),
            d.get("selftext", "")[:SNIPPET_LIMIT],
            sub_comments=sub_comments,
            timestamp=datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat() if created_utc else None,
        ))

    log.info(f"  Reddit {subreddit} '{query}' → {len(results)} results")
    return results


def save_csv(findings: list[Finding], path: str) -> None:
    # Step 6.1: Persist raw crawl findings to CSV.
    if not findings:
        log.info("No findings to save.")
        return
    col_names = [f.name for f in fields(Finding)]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=col_names)
        writer.writeheader()
        for f in findings:
            writer.writerow({k: getattr(f, k) for k in col_names})
    log.info(f"Saved {len(findings)} rows → {path}")

def run():
    # Step 1: Initialize in-memory containers.
    all_findings: list[Finding] = []
    seen: set[str] = set()

    def add(findings):
        # Step 2: Deduplicate by stable hash and keep only unique records.
        for f in findings:
            if f.result_hash not in seen:
                seen.add(f.result_hash)
                all_findings.append(f)
                flag_note = f"  ⚠  {f.red_flags}" if f.red_flags else ""
                log.info(f" + {f.title[:65]}{flag_note}")

    # Step 3: Run DuckDuckGo query batch.
    log.info(f"\n DuckDuckGo ({len(DDG_QUERIES)} queries) ──")
    for query in DDG_QUERIES:
        add(search_duckduckgo(query))
        time.sleep(REQUEST_DELAY)

    # Safety net: if strict DDG seeds return nothing, try broader DDG queries.
    ddg_count = sum(1 for finding in all_findings if finding.source == "duckduckgo")
    if ddg_count == 0:
        log.info("  DDG yielded 0 results, running fallback queries...")
        for query in DDG_FALLBACK_QUERIES:
            add(search_duckduckgo(query))
            time.sleep(REQUEST_DELAY)

    # Step 4: Run global Reddit query batch.
    log.info(f"\n Reddit global search ({len(REDDIT_QUERIES)} queries)")
    for query in REDDIT_QUERIES:
        add(search_reddit(query))
        time.sleep(REQUEST_DELAY)

    # Step 5: Run subreddit-scoped query batch.
    log.info(f"\n Reddit subreddit search")
    for sub in REDDIT_SUBREDDITS:
        for query in ["for sale", "selling", "WTB"]:
            add(search_reddit_subreddit(sub, query))
            time.sleep(REQUEST_DELAY)

    # Step 6: Summarize crawl output.
    flagged = [f for f in all_findings if f.red_flags or f.species_hits]
    log.info(f"Total unique results : {len(all_findings)}")
    log.info(f"With flags/species   : {len(flagged)}")

    # Step 7: Build one combined dataset and save a single final CSV.
    analysis_rows = build_expected_fields_rows(all_findings)
    save_expected_fields_csv(analysis_rows, OUTPUT_CSV)
    log.info(f"Combined output file: {OUTPUT_CSV}")

# 3. TOP 20 QUESTIONS MAPPING (For filtering and analysis)
question_map = {
    "Q1_Sentiment": ["love", "want", "dangerous", "cruel", "cool", "illegal"],
    "Q2_Themes": ["legality", "danger", "care", "cost", "welfare", "conservation"],
    "Q3_Motivation": ["want one", "dream pet", "unique", "status", "rare"],
    "Q4_Legal_Risk": ["illegal", "banned", "permit", "license", "law", "regulated", "confiscated", "seized"],
    "Q5_Personal_Safety_Risk": [
        "attack", "bite", "scratch", "venom", "dangerous", "injury", "hospital", "disease", "zoonotic", "risk to owner"
    ],
    "Q6_Animal_Welfare": ["cruelty", "suffering", "captivity", "neglect", "care needs", "poor conditions"],
    "Q7_Conservation": ["endangered", "extinction", "wildlife trafficking", "conservation", "iucn", "cites"],
    "Q8_Pet_Category": ["big cat pet", "tiger pet", "lion pet", "jaguar pet", "cheetah pet", "serval pet"],
    "Q9_Species": ["species", "breed", "animal type"],
    "Q9A_Big_Cats": ["tiger", "lion", "jaguar", "cheetah", "baby tiger", "pet tiger", "big cat pet"],
    "Q9B_Primates": [
        "capuchin monkey pet", "chimpanzee pet", "gibbon pet", "lar gibbon pet", "howler monkey pet", "lemur pet",
        "ring-tailed lemur pet", "marmoset pet", "pygmy marmoset pet", "macaque pet", "pigtail macaque pet",
        "slow loris pet", "squirrel monkey pet", "vervet monkey pet", "bush baby pet", "kinkajou pet"
    ],
    "Q9C_Parrots_And_Birds": [
        "african grey parrot pet", "cockatoo pet", "sulfur crested cockatoo pet", "umbrella cockatoo pet",
        "moluccan cockatoo pet", "salmon-crested cockatoo pet", "scarlet macaw pet", "military macaw pet",
        "great green macaw pet", "hyacinth macaw pet", "yellow-naped amazon pet", "yellow-headed amazon pet",
        "painted bunting pet", "red siskin pet", "orange-fronted parakeet pet", "macaw pet", "amazon parrot pet"
    ],
    "Q9D_Turtles_Tortoises": [
        "bog turtle pet", "box turtle pet", "eastern box turtle pet", "mexican box turtle pet", "striped mud turtle pet",
        "musk turtle pet", "painted turtle pet", "slider turtle pet", "hispaniolan slider pet", "spotted turtle pet",
        "radiated tortoise pet", "russian steppe tortoise pet", "mata mata turtle pet", "orinoco mata mata pet"
    ],
    "Q9E_Reptiles": ["python pet", "burmese python pet", "monitor lizard pet", "savannah monitor pet", "alligator lizard pet"],
    "Q9F_Amphibians": ["pebas stubfoot toad pet", "golden mantella pet", "harlequin frog pet", "poison dart frog pet", "glass frog pet"],
    "Q10_Platform": ["metadata only"],
    "Q11_Sentiment_By_Category": ["positive", "negative"],
    "Q12_Sentiment_By_Platform": ["reddit opinion", "youtube comment"],
    "Q13_Language_Patterns": ["scary", "cool", "expensive", "responsibility"],
    "Q14_Stance": ["support", "oppose", "neutral"],
    "Q15_Regulation_Awareness": ["law", "rules", "allowed", "banned", "permit"],
    "Q16_Knowledge_Gaps": ["didn't know", "unaware", "confused"],
    "Q17_Responsibility": ["care", "training", "commitment"],
    "Q18_Benefits": ["unique", "exotic", "rare"],
    "Q19_Challenges": ["cost", "danger", "maintenance"],
    "Q20_Purchasing_Channels": ["breeder", "for sale", "expo"],
}


# Category map used by Q8 classification.
category_map = {
    "Big Cats": question_map["Q9A_Big_Cats"],
    "Primates": question_map["Q9B_Primates"],
    "Parrots & Birds": question_map["Q9C_Parrots_And_Birds"],
    "Turtles/Tortoises": question_map["Q9D_Turtles_Tortoises"],
    "Reptiles": question_map["Q9E_Reptiles"],
    "Amphibians": question_map["Q9F_Amphibians"],
}


# Important columns:
# platform,keyword_used,category,video_id,video_title,video_description,comment_id,text_content,comment_date,source_url,
# country_context,location_geographic,red_flags,species_hits,timestamp,result_hash,

def infer_pet_category(text: str) -> str:
    """Return a Q8-style category label based on species keyword hits."""
    lower = text.lower()
    for category, keywords in category_map.items():
        if any(keyword in lower for keyword in keywords):
            return category
    return "Other"

# Combine all all datasets (csv files) and save to a single CSV
def build_expected_fields_rows(findings: list[Finding]) -> list[dict[str, str]]:
    """Create analysis rows with sentiment + question mapping from collected findings."""
    analyzer = SentimentIntensityAnalyzer()
    rows: list[dict[str, str]] = []

    # Step A: Transform each raw finding into the expected analysis schema.
    for finding in findings:
        full_text = f"{finding.title} {finding.snippet}".strip().lower()
        mapped_questions = [
            question
            for question, keywords in question_map.items()
            if any(keyword in full_text for keyword in keywords)
        ]

        rows.append({
            "platform": finding.source,
            "keyword_used": finding.query,
            "category": infer_pet_category(full_text),
            "video_id": "",
            "video_title": finding.title,
            "video_description": "",
            "comment_id": "",
            "text_content": full_text,
            "comment_date": finding.timestamp.split("T")[0],
            "source_url": finding.url,
            "country_context": "unknown",
            "location_geographic": "unknown",
            "red_flags": finding.red_flags,
            "species_hits": finding.species_hits,
            "sub_comments": finding.sub_comments,
            "timestamp": finding.timestamp,
            "result_hash": finding.result_hash,
            "sentiment_score": f"{analyzer.polarity_scores(full_text)['compound']:.4f}",
            "questions_mapped": "|".join(mapped_questions),
        })

    return rows


def save_expected_fields_csv(rows: list[dict[str, str]], path: str) -> None:
    """Persist the expected analysis dataset as CSV."""
    if not rows:
        log.info("No analysis rows to save.")
        return

    fieldnames = list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    log.info(f"Saved {len(rows)} analysis rows → {path}")



if __name__ == "__main__":
    run()