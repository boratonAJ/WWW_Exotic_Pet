# Project Structure Guide

## Directory Overview

### `/data`
**Purpose**: Store all project data

- **`raw/`**: Original, immutable source data. Never modify files here.
- **`processed/`**: Cleaned and transformed data ready for modeling.
- **`external/`**: Third-party or reference datasets.

### `/notebooks`
**Purpose**: Jupyter notebooks for exploration, analysis, and reporting

- Use numbered prefixes: `01_exploration.ipynb`, `02_modeling.ipynb`
- One clear purpose per notebook
- Include markdown cells with objectives and findings
- Clean output before committing (for version control)

### `/src`
**Purpose**: Reusable Python modules and utilities

- `data.py`: Data loading and preprocessing
- `utils.py`: General utility functions
- `models.py`: Model training and evaluation
- `visualization.py`: Plotting functions
- Keep functions well-documented with docstrings

### `/models`
**Purpose**: Trained model artifacts and serialized objects

- Save models with timestamps: `model_v1_20240101.pkl`
- Include metadata files: model parameters, performance metrics
- Example: `xgboost_model_v1.pkl`, `scaler_v1.pkl`

### `/results`
**Purpose**: Output and analysis results

- **`figures/`**: Generated plots, graphs, visualizations
- **`reports/`**: Final analysis reports, summaries, presentations

### `/tests`
**Purpose**: Unit and integration tests

- Mirror the structure of `/src`
- Name files as `test_*.py`
- Run with: `pytest`

### `/docs`
**Purpose**: Project documentation

- `STRUCTURE.md`: This file
- `METHODOLOGY.md`: Approach and assumptions
- `API.md`: Function/module documentation
- `SETUP.md`: Environment setup instructions

### `/configs`
**Purpose**: Configuration files for reproducibility

- `default.yaml`: Default parameters
- `experiment_*.yaml`: Experiment-specific configs
- Use YAML format for human readability

### `/scripts`
**Purpose**: Standalone Python scripts for automation

- Data processing workflows
- Model training pipelines
- Data preparation scripts
- Use command-line arguments for flexibility

## Best Practices

### Data Management
- Never commit raw data files to git
- Document data sources and transformations
- Keep data lineage clear
- Use `.gitkeep` to preserve empty directories

### Version Control
- Commit code, not data or models
- Use `.gitignore` to exclude large files
- Write meaningful commit messages
- Document changes in notebooks with markdown

### Reproducibility
- Use `requirements.txt` for dependencies
- Set random seeds in code
- Store configuration in YAML files
- Document assumptions clearly

### Collaboration
- Use clear naming conventions
- Write docstrings for all functions
- Add comments for complex logic
- Keep notebooks organized and numbered
- Use feature branches for new work

## Workflow Example

```bash
1. Load raw data: data/raw/
2. Explore: notebooks/01_exploration.ipynb
3. Process: scripts/data_processing.py → data/processed/
4. Model: notebooks/02_modeling.ipynb
5. Evaluate: notebooks/03_evaluation.ipynb
6. Save: models/, results/figures/, results/reports/
```
