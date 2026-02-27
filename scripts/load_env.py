"""Small helper to load environment variables from a .env file.

Usage:
    python scripts/load_env.py        # loads .env and prints SERPAPI_KEY present

This uses python-dotenv (already in requirements.txt).
"""
import os
from dotenv import load_dotenv

# Load .env from repository root
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(env_path)

key = os.environ.get("SERPAPI_KEY")
if not key:
    print("SERPAPI_KEY not set. Copy .env.example to .env and add your key.")
else:
    print("SERPAPI_KEY loaded from .env (hidden)")
