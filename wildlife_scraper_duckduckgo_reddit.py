import csv
import time
import hashlib
import logging
from datetime import datetime
from dataclasses import dataclass, fields
from urllib.parse import unquote, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

OUTPUT_CSV    = f"wildlife_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
REQUEST_DELAY = 3      # seconds between requests incase you get rate limited
DDG_RESULTS   = 10     # max results per DuckDuckGo query
REDDIT_LIMIT  = 10     # posts per Reddit query
SNIPPET_LIMIT = 400 

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

DDG_QUERIES = [
    '"exotic pet" "for sale" "no papers" site:quora.com',
    '"slow loris" "for sale" OR "pet"',
    '"pangolin" "for sale" OR "available"',
    '"baby monkey" "for sale" "contact"',
    '"African grey" "unringed" "for sale"',
    '"tortoise" "for sale" "no paperwork"',
    '"tiger cub" "for sale" OR "adopt"',
    '"kinkajou" "for sale" "shipping"',
    '"chameleon" "for sale" "live arrival"',
    '"exotic" "reptile" "discreet shipping"',
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
    timestamp:    str
    result_hash:  str

def make_hash(url: str, query: str) -> str:
    return hashlib.md5(f"{url}|{query}".encode()).hexdigest()[:12]


def check_flags(text: str) -> tuple[list[str], list[str]]:
    lower = text.lower()
    flags   = [t for t in RED_FLAG_TERMS if t in lower]
    species = [s for s in SPECIES_TERMS  if s in lower]
    return flags, species


def make_finding(source, query, url, title, snippet) -> Finding:
    flags, species = check_flags(f"{title} {snippet}")
    return Finding(
        source       = source,
        query        = query,
        url          = url,
        title        = title[:200],
        snippet      = snippet[:SNIPPET_LIMIT],
        red_flags    = ", ".join(sorted(set(flags))),
        species_hits = ", ".join(sorted(set(species))),
        timestamp    = datetime.utcnow().isoformat(),
        result_hash  = make_hash(url, query),
    )

def search_duckduckgo(query: str) -> list[Finding]:
    """
    Scrapes DuckDuckGo HTML results. No API key required.
    Uses the html.duckduckgo.com endpoint which returns plain HTML.
    """
    url = "https://html.duckduckgo.com/html/"
    try:
        r = requests.post(url, data={"q": query}, headers=HEADERS, timeout=15)
        r.raise_for_status()
    except Exception as e:
        log.warning(f"DDG request failed: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    results = []

    for result in soup.select(".result")[:DDG_RESULTS]:
        a_tag   = result.select_one(".result__title a")
        snip    = result.select_one(".result__snippet")
        if not a_tag:
            continue
        title   = a_tag.get_text(strip=True)
        href    = a_tag.get("href", "")
        snippet = snip.get_text(strip=True) if snip else ""

        # DDG wraps destination URLs
        if "uddg=" in href:
            qs = parse_qs(urlparse(href).query)
            href = unquote(qs.get("uddg", [href])[0])

        results.append(make_finding("duckduckgo", query, href, title, snippet))

    log.info(f"  DDG '{query[:55]}' → {len(results)} results")
    return results

def search_reddit(query: str) -> list[Finding]:
    """
    Uses Reddit's public search JSON endpoint.
    No authentication required for read-only queries.
    """
    url = "https://www.reddit.com/search.json"
    params = {"q": query, "sort": "new", "limit": REDDIT_LIMIT, "type": "link"}
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        posts = r.json().get("data", {}).get("children", [])
    except Exception as e:
        log.warning(f"Reddit search failed: {e}")
        return []

    results = []
    for post in posts:
        d = post.get("data", {})
        results.append(make_finding(
            "reddit", query,
            "https://reddit.com" + d.get("permalink", ""),
            d.get("title", ""),
            d.get("selftext", "")[:SNIPPET_LIMIT],
        ))

    log.info(f"  Reddit '{query[:55]}' → {len(results)} results")
    return results


def search_reddit_subreddit(subreddit: str, query: str) -> list[Finding]:
    """Search within a specific subreddit using the public JSON API."""
    url = f"https://www.reddit.com/{subreddit}/search.json"
    params = {"q": query, "restrict_sr": "on", "limit": REDDIT_LIMIT}
    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        posts = r.json().get("data", {}).get("children", [])
    except Exception as e:
        log.warning(f"Reddit subreddit request failed ({subreddit}): {e}")
        return []

    results = []
    for post in posts:
        d = post.get("data", {})
        results.append(make_finding(
            "reddit", f"{subreddit}: {query}",
            "https://reddit.com" + d.get("permalink", ""),
            d.get("title", ""),
            d.get("selftext", "")[:SNIPPET_LIMIT],
        ))

    log.info(f"  Reddit {subreddit} '{query}' → {len(results)} results")
    return results


def save_csv(findings: list[Finding], path: str) -> None:
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
    all_findings: list[Finding] = []
    seen: set[str] = set()

    def add(findings):
        for f in findings:
            if f.result_hash not in seen:
                seen.add(f.result_hash)
                all_findings.append(f)
                flag_note = f"  ⚠  {f.red_flags}" if f.red_flags else ""
                log.info(f" + {f.title[:65]}{flag_note}")

    log.info(f"\n DuckDuckGo ({len(DDG_QUERIES)} queries) ──")
    for query in DDG_QUERIES:
        add(search_duckduckgo(query))
        time.sleep(REQUEST_DELAY)

    log.info(f"\n Reddit global search ({len(REDDIT_QUERIES)} queries)")
    for query in REDDIT_QUERIES:
        add(search_reddit(query))
        time.sleep(REQUEST_DELAY)

    log.info(f"\n Reddit subreddit search")
    for sub in REDDIT_SUBREDDITS:
        for query in ["for sale", "selling", "WTB"]:
            add(search_reddit_subreddit(sub, query))
            time.sleep(REQUEST_DELAY)
    flagged = [f for f in all_findings if f.red_flags or f.species_hits]
    log.info(f"Total unique results : {len(all_findings)}")
    log.info(f"With flags/species   : {len(flagged)}")

    save_csv(all_findings, OUTPUT_CSV)
    log.info(f"Output file: {OUTPUT_CSV}")


if __name__ == "__main__":
    run()