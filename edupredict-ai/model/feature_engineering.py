import pandas as pd
import numpy as np
import os
import logging
from pathlib import Path
from model.data_builder import IndianStudentDataset
from config import EnvConfig

from model.feature_pipeline import FeaturePipeline

logger = logging.getLogger(__name__)

FEATURE_COLS_V5 = [
    "cgpa_normalized", "internships_count", "backlogs",
    "median_salary_normalized", "potential_score", "demand_proxy",
    "placement_rate_for_field", "demand_velocity_per_day",
    "demand_acceleration", "velocity_r_squared", "demand_momentum", 
    "market_hhi", "macro_index", "backlogs_missing"
]

assert FEATURE_COLS_V5 == FeaturePipeline.feature_names(), "Feature columns mismatch!"

def add_temporal_features_static(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds zero-value temporal columns so the schema is complete before temporal DAG runs.
    Ensures training data matches inference schema.
    """
    df = df.copy()
    defaults = {
        "demand_proxy": 0.5,
        "median_salary_normalized": 0.5,
        "demand_velocity_per_day": 0.0,
        "demand_acceleration": 0.0,
        "velocity_r_squared": 0.0,
        "demand_momentum": 0.5,
        "market_hhi": 0.143, # 1/7 fields
        "backlogs_missing": 0
    }
    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val
    return df

def build_master_dataset(raw_data_dir):
    """
    Authoritative data pipeline for training.
    Replaces old random-sampling logic with authentic Indian student data.
    """
    logger.info(f"Building master dataset from {raw_data_dir}...")
    
    # 1. Load authentic Indian dataset
    ds = IndianStudentDataset(data_dir=Path(raw_data_dir))
    df = ds.load()
    
    # 2. Add static temporal placeholders
    df = add_temporal_features_static(df)
    
    # 3. Add macro index (training-time snapshot)
    df["macro_index"] = float(EnvConfig.IMRI_DEFAULT())
    
    # 4. Standardize column names (from data_builder to FEATURE_COLS_V5)
    if "median_salary_inr" in df.columns and "median_salary_normalized" not in df.columns:
        from model.data_builder import NIRF_SALARY_P5_INR, NIRF_SALARY_P95_INR
        df["median_salary_normalized"] = (
            (df["median_salary_inr"] - NIRF_SALARY_P5_INR) / 
            (NIRF_SALARY_P95_INR - NIRF_SALARY_P5_INR)
        ).clip(0, 1)

    # Recompute potential_score using V5 logic
    df["potential_score"] = FeaturePipeline.compute_potential_score(
        df["cgpa_normalized"],
        df["internships_count"],
        df["placement_rate_for_field"],
        df["median_salary_normalized"]
    )
    
    # Update momentum if velocity is present
    df["demand_momentum"] = FeaturePipeline.compute_momentum(
        df["demand_proxy"],
        np.clip((df["demand_velocity_per_day"] + 50) / 100, 0, 1)
    )

    # 5. Save
    os.makedirs("data/processed", exist_ok=True)
    df.to_csv("data/processed/features.csv", index=False)
    
    logger.info(f"Final training set shape: {df.shape}")
    return df

if __name__ == "__main__":
    import logging_config
    logging_config.configure_logging()
    build_master_dataset("data/raw")
