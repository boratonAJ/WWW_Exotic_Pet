#!/usr/bin/env python3
"""Simple CLI wrapper to run the combined Quora scraper.

Usage:
  python scripts/run_quora_scraper.py                # runs default keywords from combined script
  python scripts/run_quora_scraper.py --keywords "pet monkey,pet tiger"
  python scripts/run_quora_scraper.py --file keywords.txt

The script loads `scripts/scrape_quora_combined.py` and calls `collect_for_keywords()`.
"""
import argparse
import os
import importlib.util


def load_module_from_path(path):
    spec = importlib.util.spec_from_file_location('scrape_quora_combined', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    ap = argparse.ArgumentParser(description='Run combined Quora scraper with keywords or file')
    ap.add_argument('--keywords', '-k', help='Comma-separated keywords (e.g. "pet monkey,pet tiger")')
    ap.add_argument('--file', '-f', help='File with one keyword per line')
    ap.add_argument('--output', '-o', default='WWF_Quora_Crawl_Combined.csv')
    args = ap.parse_args()

    script_path = os.path.join(os.path.dirname(__file__), 'scrape_quora_combined.py')
    mod = load_module_from_path(script_path)

    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(',') if k.strip()]
    elif args.file:
        with open(args.file, 'r', encoding='utf-8') as f:
            keywords = [line.strip() for line in f if line.strip()]
    else:
        # fall back to building the same small keywords used in the combined script
        keywords = []
        for cat, sl in mod.species_to_categories.items():
            if sl:
                keywords.append(f'pet {sl[0]}')
        keywords.extend(['pet monkey', 'exotic pet ownership'])

    print('Running scraper for', len(keywords), 'keywords')
    mod.collect_for_keywords(keywords, output=args.output)


if __name__ == '__main__':
    main()
