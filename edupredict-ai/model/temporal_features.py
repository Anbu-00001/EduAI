import os
import json
import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

def compute_demand_velocity(cache_dir="data/pipeline/history"):
    if not os.path.exists(cache_dir):
        return pd.DataFrame()
    
    files = sorted([f for f in os.listdir(cache_dir) if f.startswith("snapshot_")])
    if len(files) < 2:
        # Return dummy zeros but with correct structure
        from data.pipeline.dag import FIELD_QUERIES
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
            data = json.load(j)
            for rec in data["records"]:
                rec["timestamp"] = ts
                all_data.append(rec)
    
    df = pd.DataFrame(all_data)
    results = []
    
    for field in df["field"].unique():
        f_df = df[df["field"] == field].sort_values("timestamp")
        t = (f_df["timestamp"] - f_df["timestamp"].min()) / 86400.0 # days
        c = f_df["job_count_consensus"]
        
        # OLS slope: beta = sum((t-t_bar)*(c-c_bar)) / sum((t-t_bar)**2)
        t_bar = t.mean()
        c_bar = c.mean()
        beta = np.sum((t - t_bar) * (c - c_bar)) / (np.sum((t - t_bar)**2) + 1e-9)
        
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
            v1 = (f_df.iloc[mid]["job_count_consensus"] - f_df.iloc[0]["job_count_consensus"]) / ((f_df.iloc[mid]["timestamp"] - f_df.iloc[0]["timestamp"]) / 86400.0)
            v2 = (f_df.iloc[-1]["job_count_consensus"] - f_df.iloc[mid]["job_count_consensus"]) / ((f_df.iloc[-1]["timestamp"] - f_df.iloc[mid]["timestamp"]) / 86400.0)
            accel = v2 - v1
            
        results.append({
            "field": field,
            "demand_velocity_per_day": beta,
            "demand_acceleration": accel,
            "velocity_r_squared": float(r2),
            "velocity_estimated": False
        })
        
    return pd.DataFrame(results)

def compute_hhi(demand_df):
    counts = demand_df["job_count_consensus"]
    total = counts.sum()
    if total == 0: return 1.0/len(demand_df)
    shares = counts / total
    hhi = np.sum(shares**2)
    return float(hhi)

def build_peer_cohort_graph(X_train, y_train, X_query, sigma=None, top_k=50):
    X_train = np.atleast_2d(X_train)
    X_query = np.atleast_2d(X_query)
    
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

def add_temporal_features(feature_df, velocity_df, demand_df):
    if velocity_df.empty:
        # If no velocity yet, just merge demand_proxy and set others to 0
        feature_df["demand_velocity_per_day"] = 0.0
        feature_df["demand_acceleration"] = 0.0
        feature_df["velocity_r_squared"] = 0.0
        feature_df["demand_momentum"] = 0.7 * feature_df["demand_proxy"]
        feature_df["market_hhi"] = 1.0 / 7.0
        return feature_df
    
    # Merge velocity
    df = feature_df.merge(velocity_df, on="field", how="left")
    
    # demand_momentum = 0.3*velocity + 0.7*demand_proxy
    # Need to scale velocity to same range as demand_proxy (0-1) roughly
    v_min = velocity_df["demand_velocity_per_day"].min()
    v_max = velocity_df["demand_velocity_per_day"].max()
    v_scaled = (df["demand_velocity_per_day"] - v_min) / (v_max - v_min + 1e-9)
    
    df["demand_momentum"] = 0.3 * v_scaled + 0.7 * df["demand_proxy"]
    df["market_hhi"] = compute_hhi(demand_df)
    
    return df.fillna(0.0)
