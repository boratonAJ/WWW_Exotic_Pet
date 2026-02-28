# Project Name

## Overview
Brief description of the project and its objectives.

## Project Structure

```
.
├── data/
│   ├── raw/              # Original, immutable data
│   ├── processed/        # Transformed data ready for analysis
│   └── external/         # Data from external sources
├── notebooks/            # Jupyter notebooks for exploration and reporting
├── src/                  # Reusable Python modules
├── models/               # Trained model artifacts
├── results/
│   ├── figures/          # Generated plots and visualizations
│   └── reports/          # Reports, analysis documents
├── tests/                # Unit tests
├── docs/                 # Project documentation
├── configs/              # Configuration files
├── scripts/              # Standalone scripts
├── .gitignore
├── requirements.txt
├── setup.py
└── README.md
```

### Directory Overview

#### `/data`
Store all project datasets with clear separation:
- **`raw/`**: Original, immutable source data. Never modify files here.
- **`processed/`**: Cleaned and transformed data ready for modeling.
- **`external/`**: Third-party or reference datasets.

#### `/notebooks`
Jupyter notebooks for exploration, analysis, and reporting:
- Use numbered prefixes: `01_exploration.ipynb`, `02_modeling.ipynb`
- One clear purpose per notebook
- Include markdown cells with objectives and findings
- Clean output before committing

#### `/src`
Reusable Python modules and utilities:
- `data.py`: Data loading and preprocessing
- `utils.py`: General utility functions
- `models.py`: Model training and evaluation
- `visualization.py`: Plotting functions
- Keep functions well-documented with docstrings

#### `/models`
Trained model artifacts and serialized objects:
- Save models with timestamps: `model_v1_20240101.pkl`
- Include metadata files with model parameters and performance metrics

#### `/results`
Output and analysis results:
- **`figures/`**: Generated plots, graphs, and visualizations
- **`reports/`**: Final analysis reports, summaries, and presentations

#### `/tests`
Unit and integration tests:
- Mirror the structure of `/src`
- Name files as `test_*.py`
- Run with: `pytest`

#### `/docs`
Project documentation:
- `STRUCTURE.md`: Detailed structure guide
- `METHODOLOGY.md`: Approach and assumptions
- `API.md`: Function/module documentation

#### `/configs`
Configuration files for reproducibility:
- `default.yaml`: Default parameters
- `experiment_*.yaml`: Experiment-specific configs
- Use YAML format for human readability

#### `/scripts`
Standalone Python scripts for automation:
- Data processing workflows
- Model training pipelines
- Data preparation scripts

## Quick Start

### Installation
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Running Analysis
```bash
# Run notebooks
jupyter notebook notebooks/

# Run scripts
python scripts/data_processing.py
```

### Environment variables

- `SERPAPI_KEY` — Set this environment variable to your SerpApi API key before running crawlers or the notebook. Example:

```bash
export SERPAPI_KEY=your_real_key_here
```

Do not commit API keys to source control; the notebook and scripts read the key from `SERPAPI_KEY`.

### Commands to run locally

1. Copy the example env file and set your SerpApi key:

```bash
cp .env.example .env
# then edit .env and set SERPAPI_KEY
```

2. Verify the key loads (uses `python-dotenv`):

```bash
python scripts/load_env.py
```

3. Run the SerpApi crawl (will use `SERPAPI_KEY` and consume credits):

```bash
python scripts/run_serpapi_crawl.py
```

4. Open notebooks for exploration:

```bash
jupyter notebook notebooks/
```

### Selenium fallback (optional)

If the requests-based Quora scraper misses content (Quora is JS-heavy), use the Selenium fallback script which runs a headless Chrome browser to render pages before scraping.

1. Ensure Chrome/Chromium is installed for your platform (macOS example):

```bash
# Install Chrome on macOS (Intel or Apple Silicon) via Homebrew
brew install --cask google-chrome
```

2. Install Python dependencies (includes `selenium` and `webdriver-manager`):

```bash
python3 -m pip install -r requirements.txt
```

3. If you previously ran the Selenium script and hit a chromedriver/architecture mismatch (Exec format errors), remove webdriver-manager's cached drivers so it will redownload the correct binary:

```bash
rm -rf ~/.wdm/drivers/chromedriver
```

4. Run the Selenium fallback (non-headless mode is useful for debugging — edit `scripts/scrape_quora_selenium.py` and set `headless=False` in `get_driver()`):

```bash
python3 scripts/scrape_quora_selenium.py
```

Troubleshooting:
- If you see `Exec format error`, it usually means the downloaded chromedriver binary doesn't match your CPU architecture (Intel vs Apple Silicon). Deleting `~/.wdm/drivers/chromedriver` and reinstalling Chrome then re-running will usually fix it.
- For debugging, run with `headless=False` and watch the browser to confirm pages load.
- If Chrome is not installed or not on PATH, `webdriver-manager` may download drivers that won't run — ensure a matching Chrome browser is installed.

### CLI wrapper for Quora scraper

A simple CLI wrapper is provided to run the combined Quora scraper with custom keywords or a file of keywords. The wrapper calls `scripts/scrape_quora_combined.py` and writes `WWF_Quora_Crawl_Combined.csv` by default.

Usage examples:

```bash
# Run built-in small keyword set
python3 scripts/run_quora_scraper.py

# Pass comma-separated keywords
python3 scripts/run_quora_scraper.py --keywords "pet monkey,pet tiger"

# Read keywords from a file (one per line)
python3 scripts/run_quora_scraper.py --file keywords.txt

# Specify custom output file
python3 scripts/run_quora_scraper.py --keywords "pet monkey" --output my_results.csv
```

Notes:
- The scraper first tries a lightweight `requests` parse and falls back to Selenium if pages require rendering.
- Ensure dependencies are installed (`pip install -r requirements.txt`) and Chrome is available for Selenium fallback.


Notes:
- Keep your `.env` private — it's already listed in `.gitignore`.
- If you prefer not to use `.env`, export `SERPAPI_KEY` directly in your shell.

## Dependencies
See [requirements.txt](requirements.txt) for Python dependencies.

## Authors
- Olabode Ajayi : Email.........
- vaishnavi.pachva@gwmail.gwu.edu
- Henry.lin@gwmail.gwu.edu
- c.buss@gwmail.gwu.edu
- kittyyangjunbi@gwmail.gwu.edu
- david.king@gwmail.gwu.edu

## License
See LICENSE file for details.

## Contributing
1. Create a feature branch
2. Make changes and commit
3. Push to remote and create a pull request

## Notes
- Keep raw data immutable
- Version control notebooks carefully
- Document assumptions and decisions
- Use config files for parameters
