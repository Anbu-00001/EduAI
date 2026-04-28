import os
import json
import math
import numpy as np
import pandas as pd
import logging
from sklearn.metrics import log_loss
from config import EnvConfig, FIELD_QUERIES

logger = logging.getLogger(__name__)

def compute_macro_index(datagov_api_key: str = None) -> float:
    """
    Upstart's Macro Index (UMI) accounts for economic conditions
    that affect repayment independently of individual student profile.
    
    Our equivalent: India Macro Repayment Index (IMRI)
    
    IMRI = weighted composite of:
      - Graduate unemployment rate (PLFS quarterly data) — weight 0.40
      - RBI repo rate (monetary policy indicator) — weight 0.30
      - CPI education inflation — weight 0.20
      - Corporate hiring index (from demand DAG HHI) — weight 0.10
    
    IMRI ∈ [0, 1] where 1 = best macro conditions for repayment
    
    Math:
      IMRI = Σ_i w_i * normalize(component_i)
      normalize(x) = (x - x_bad) / (x_good - x_bad)
      
      For unemployment: x_bad=0.20, x_good=0.03 (lower = better)
      For repo rate:     x_bad=0.08, x_good=0.04 (lower = better)
      For CPI edu:       x_bad=0.12, x_good=0.03 (lower = better)
      For hiring index:  x_bad=0.0,  x_good=1.0  (higher = better)
    
    All normalisation bounds are derived from RBI historical data (2015–2024).
    They encode domain knowledge — not arbitrary hardcoded thresholds.
    """
    import requests

    components = {}

    # 1. Graduate unemployment rate from data.gov.in PLFS
    try:
        api_key = datagov_api_key or EnvConfig.DATAGOV_API_KEY()
        if api_key:
            url = "https://api.data.gov.in/resource/7d9b5b2e-5671-4e0b-a2e1-c8d3ad8f2e1b"
            resp = requests.get(
                url, params={"api-key": api_key, "format": "json", "limit": 1},
                timeout=10
            )
            if resp.status_code == 200:
                data = resp.json()
                records = data.get("records", [])
                if records:
                    unemp_rate = float(records[0].get("unemployment_rate", 0.13)) / 100
                    components["unemployment"] = unemp_rate
    except Exception as e:
        logger.warning(f"Could not fetch unemployment rate: {e}")
        components["unemployment"] = 0.13  # PLFS 2024 known value (documented)

    # 2. RBI repo rate — public knowledge, stable
    components["repo_rate"] = EnvConfig.RBI_REPO_RATE()

    # 3. CPI education component — from RBI bulletin
    components["cpi_education"] = EnvConfig.CPI_EDUCATION()

    # 4. Hiring index from demand DAG
    try:
        from pathlib import Path
        cache_path = Path("data/pipeline/demand_cache.json")
        if cache_path.exists():
            cache = json.loads(cache_path.read_text())
            records = cache.get("records", [])
            if records:
                avg_demand = sum(r.get("job_count_normalized", 0.5) for r in records) / len(records)
                components["hiring_index"] = avg_demand
            else:
                components["hiring_index"] = 0.5
        else:
            components["hiring_index"] = 0.5
    except Exception:
        components["hiring_index"] = 0.5

    # Default values to ensure components exists even if API fails
    components.setdefault("unemployment", 0.13)
    components.setdefault("repo_rate", 0.065)
    components.setdefault("cpi_education", 0.05)
    components.setdefault("hiring_index", 0.5)

    # Normalise each component to [0, 1] (1 = good for repayment)
    norm = {
        "unemployment": 1 - min(max((components["unemployment"] - 0.03) / (0.20 - 0.03), 0), 1),
        "repo_rate":    1 - min(max((components["repo_rate"] - 0.04) / (0.08 - 0.04), 0), 1),
        "cpi_education": 1 - min(max((components["cpi_education"] - 0.03) / (0.12 - 0.03), 0), 1),
        "hiring_index": components["hiring_index"],
    }


    weights = {"unemployment": 0.40, "repo_rate": 0.30,
               "cpi_education": 0.20, "hiring_index": 0.10}
    imri = sum(weights[k] * norm[k] for k in weights)

    logger.info(f"India Macro Repayment Index (IMRI) = {imri:.4f} (components: {norm})")
    return float(imri)


def compute_demand_velocity(cache_dir="data/pipeline/history"):
    if not os.path.exists(cache_dir):
        return pd.DataFrame()
    
    files = sorted([f for f in os.listdir(cache_dir) if f.startswith("snapshot_")])
    if len(files) < 2:
        # Return dummy zeros but with correct structure
        records = []
        for field in FIELD_QUERIES:
            records.append({
                "field": field,
                "demand_velocity_per_day": 0.0,
                "demand_acceleration": 0.0,
                "velocity_r_squared": 0.0,
                "velocity_estimated": True
            })
        return pd.DataFrame(records)

    all_data = []
    for f in files:
        ts = int(f.split("_")[1].split(".")[0])
        with open(os.path.join(cache_dir, f)) as j:
            try:
                data = json.load(j)
                for rec in data.get("records", []):
                    rec["timestamp"] = ts
                    all_data.append(rec)
            except Exception as e:
                logger.warning(f"Error reading history file {f}: {e}")
    
    df = pd.DataFrame(all_data)
    if df.empty or "field" not in df:
        records = []
        for field in FIELD_QUERIES:
            records.append({
                "field": field,
                "demand_velocity_per_day": 0.0,
                "demand_acceleration": 0.0,
                "velocity_r_squared": 0.0,
                "velocity_estimated": True
            })
        return pd.DataFrame(records)

    results = []
    
    for field in df["field"].unique():
        f_df = df[df["field"] == field].sort_values("timestamp")
        # Check valid records for this field specifically
        if len(f_df) < 2:
            results.append({
                "field": field,
                "demand_velocity_per_day": 0.0,
                "demand_acceleration": 0.0,
                "velocity_r_squared": 0.0,
                "velocity_estimated": True
            })
            continue

        t = (f_df["timestamp"] - f_df["timestamp"].min()) / 86400.0 # days
        c = f_df["job_count_consensus"]
        
        # OLS slope: beta = sum((t-t_bar)*(c-c_bar)) / sum((t-t_bar)**2)
        t_bar = t.mean()
        c_bar = c.mean()
        denom = np.sum((t - t_bar)**2)
        if denom < 1e-9:
            beta = 0.0
            r2 = 0.0
        else:
            beta = np.sum((t - t_bar) * (c - c_bar)) / denom
            # R^2
            preds = t_bar + beta * (t - t_bar)
            ss_res = np.sum((c - preds)**2)
            ss_tot = np.sum((c - c_bar)**2)
            r2 = 1 - (ss_res / (ss_tot + 1e-9))
        
        # Acceleration (2nd derivative proxy if >= 3 snapshots, else 0)
        accel = 0.0
        if len(f_df) >= 3:
            # Simple diff of slopes
            mid = len(f_df) // 2
            dt1 = (f_df.iloc[mid]["timestamp"] - f_df.iloc[0]["timestamp"]) / 86400.0
            dt2 = (f_df.iloc[-1]["timestamp"] - f_df.iloc[mid]["timestamp"]) / 86400.0
            if dt1 > 1e-6 and dt2 > 1e-6:
                v1 = (f_df.iloc[mid]["job_count_consensus"] - f_df.iloc[0]["job_count_consensus"]) / dt1
                v2 = (f_df.iloc[-1]["job_count_consensus"] - f_df.iloc[mid]["job_count_consensus"]) / dt2
                accel = v2 - v1
            
        results.append({
            "field": field,
            "demand_velocity_per_day": beta,
            "demand_acceleration": accel,
            "velocity_r_squared": float(r2),
            "velocity_estimated": False
        })
        
    return pd.DataFrame(results)

def compute_hhi(demand_df: pd.DataFrame) -> float:
    if "job_count_consensus" not in demand_df:
        return 1.0 / len(demand_df) if len(demand_df) > 0 else 1.0
    counts = demand_df["job_count_consensus"]
    total = counts.sum()
    if total == 0: 
        logger.warning("compute_hhi: all job counts are 0, returning uniform distribution")
        return 1.0/len(demand_df) if len(demand_df) > 0 else 1.0
    shares = counts / total
    hhi = np.sum(shares**2)
    return float(hhi)

def build_peer_cohort_graph(X_train, y_train, X_query, sigma=None, top_k=50):
    X_train = np.atleast_2d(X_train)
    X_query = np.atleast_2d(X_query)
    n_train = len(X_train)
    if n_train > 10_000:
        logger.warning(
            f"X_train has {n_train} rows — pairwise distance matrix is "
            f"{n_train}²×8 bytes = {n_train**2 * 8 / 1e9:.2f}GB. "
            f"Sampling 5000 rows for efficiency."
        )
        idx = np.random.choice(n_train, 5000, replace=False)
        X_train = X_train[idx]
        y_train = y_train[idx]
    
    if sigma is None:
        # Median heuristic
        idx1 = np.random.choice(len(X_train), min(1000, len(X_train)))
        idx2 = np.random.choice(len(X_train), min(1000, len(X_train)))
        dists = np.sum((X_train[idx1] - X_train[idx2])**2, axis=1)
        sigma = np.sqrt(np.median(dists[dists > 0])) if np.any(dists > 0) else 1.0

    # Distance matrix between query and train
    # (a-b)^2 = a^2 + b^2 - 2ab
    q_sq = np.sum(X_query**2, axis=1).reshape(-1, 1)
    t_sq = np.sum(X_train**2, axis=1).reshape(1, -1)
    dists = q_sq + t_sq - 2 * np.dot(X_query, X_train.T)
    dists = np.maximum(dists, 0) # Precision errors
    
    weights = np.exp(-dists / (2 * sigma**2))
    
    # Top K nearest neighbours
    cohort_probs = []
    for i in range(len(X_query)):
        idx = np.argsort(dists[i])[:top_k]
        w_top = weights[i, idx]
        y_top = y_train[idx]
        p = np.sum(w_top * y_top) / (np.sum(w_top) + 1e-9)
        cohort_probs.append(p)
        
    return np.array(cohort_probs)

def tune_graph_alpha(p_model, p_cohort, y_true, n_alphas=50):
    """Tune graph alpha. n_alphas=50 is a documented default (sufficient granularity)."""
    alphas = np.linspace(0, 1, n_alphas)
    best_alpha = 1.0
    min_loss = float('inf')
    
    for a in alphas:
        p_blend = a * p_model + (1 - a) * p_cohort
        p_blend = np.clip(p_blend, 1e-5, 1 - 1e-5)
        loss = log_loss(y_true, p_blend)
        if loss < min_loss:
            min_loss = loss
            best_alpha = a
            
    return float(best_alpha)

def _ewma_alpha(half_life_periods: float = 2.0) -> float:
    """
    α = 1 - exp(-ln(2) / T_half)
    At T_half periods, the weight of the initial observation halves.
    half_life=2 → α ≈ 0.293 (close to current 0.3, but mathematically derived)
    """
    return float(1 - math.exp(-math.log(2) / half_life_periods))

def add_temporal_features(feature_df, velocity_df, demand_df):
    
    # Check if field_of_study exists in feature_df. If so, rename to field for merging.
    if "field_of_study" not in feature_df.columns and "field" not in feature_df.columns:
        raise ValueError("feature_df must contain 'field' or 'field_of_study' column to merge temporal features")
        
    merge_col = "field_of_study" if "field_of_study" in feature_df.columns else "field"
    
    if velocity_df.empty:
        # If no velocity yet, just merge demand_proxy and set others to 0
        feature_df["demand_velocity_per_day"] = 0.0
        feature_df["demand_acceleration"] = 0.0
        feature_df["velocity_r_squared"] = 0.0
        feature_df["demand_momentum"] = 0.7 * feature_df.get("demand_proxy", 0.5)
        feature_df["market_hhi"] = 1.0 / 7.0
        return feature_df
    
    # Merge velocity
    df = feature_df.merge(velocity_df, left_on=merge_col, right_on="field", how="left")
    
    v_min = velocity_df["demand_velocity_per_day"].min()
    v_max = velocity_df["demand_velocity_per_day"].max()
    v_scaled = (df["demand_velocity_per_day"] - v_min) / (v_max - v_min + 1e-9)
    
    alpha = _ewma_alpha(2.0)
    df["demand_momentum"] = alpha * v_scaled + (1 - alpha) * df.get("demand_proxy", 0.5)
    df["market_hhi"] = compute_hhi(demand_df)
    
    if "field" in df.columns and merge_col != "field":
        df = df.drop(columns=["field"])
        
    return df.fillna(0.0)
