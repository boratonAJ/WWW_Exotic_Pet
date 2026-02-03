"""Tests for data module."""

import pytest
import pandas as pd
import tempfile
from pathlib import Path
from src.data import load_data, save_data


def test_load_save_data():
    """Test loading and saving data."""
    # Create sample data
    df = pd.DataFrame({
        'col1': [1, 2, 3],
        'col2': ['a', 'b', 'c']
    })
    
    # Save and load
    with tempfile.TemporaryDirectory() as tmpdir:
        filepath = Path(tmpdir) / 'test.csv'
        save_data(df, str(filepath))
        loaded_df = load_data(str(filepath))
        
        # Check equality
        pd.testing.assert_frame_equal(df, loaded_df)
