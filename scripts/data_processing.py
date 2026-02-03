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
