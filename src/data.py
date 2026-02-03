"""
Data loading and processing utilities.
"""

import pandas as pd
from pathlib import Path


def load_data(filepath: str) -> pd.DataFrame:
    """
    Load data from file.
    
    Args:
        filepath: Path to data file
        
    Returns:
        DataFrame with loaded data
    """
    return pd.read_csv(filepath)


def save_data(df: pd.DataFrame, filepath: str) -> None:
    """
    Save data to file.
    
    Args:
        df: DataFrame to save
        filepath: Output path
    """
    df.to_csv(filepath, index=False)
