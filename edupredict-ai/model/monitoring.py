"""
Production Monitoring for EduPredict AI

Two types of drift monitored:

1. Feature drift (covariate shift):
   PSI = Σ_i (A_i - E_i) * ln(A_i/E_i)   [Population Stability Index]
   KS  = sup_x |F_train(x) - F_new(x)|     [Kolmogorov-Smirnov statistic]
   
   PSI thresholds (industry standard, used by all major Indian NBFCs):
     < 0.10  → No significant change
     < 0.25  → Moderate change — monitor
     ≥ 0.25  → Major shift — retrain
   
   KS thresholds (two-sample KS test at α=0.05):
     p-value < 0.05 → distributions differ significantly → monitor
     p-value < 0.01 → strong evidence of shift → retrain

2. Prediction drift (concept shift):
   Monitor distribution of model output probabilities over time.
   If the mean calibrated probability shifts by more than 2σ
   from the training-time mean, flag for investigation.
   
   Jensen-Shannon divergence between training and current output distribution:
   JSD(P||Q) = 0.5 * KL(P||M) + 0.5 * KL(Q||M)  where M = (P+Q)/2
   JSD ∈ [0, 1] — higher = more diverged

Monitoring is checked after each DAG run and after every 100 API calls.
If ANY feature has PSI ≥ 0.25 OR overall prediction JSD > 0.1:
  → Schedule an automated retraining run
"""

import numpy as np
import pandas as pd
import json
import logging
import time
from pathlib import Path
from scipy import stats as scipy_stats
from typing import Optional
import sqlite3

from config import DomainConstants, MONITORING_DB

logger = logging.getLogger(__name__)

TRAINING_STATS_PATH = Path("model/artifacts/training_feature_stats.json")


def save_training_stats(X_train: np.ndarray, feature_names: list, predictions: np.ndarray):
    """
    Save baseline statistics from training set.
    Called once at the end of each training run.
    These become the reference distribution for drift detection.
    """
    stats = {}
    for i, feat in enumerate(feature_names):
        col = X_train[:, i]
        stats[feat] = {
            "mean":     float(np.mean(col)),
            "std":      float(np.std(col)),
            "min":      float(np.min(col)),
            "max":      float(np.max(col)),
            "p10":      float(np.percentile(col, 10)),
            "p25":      float(np.percentile(col, 25)),
            "p50":      float(np.percentile(col, 50)),
            "p75":      float(np.percentile(col, 75)),
            "p90":      float(np.percentile(col, 90)),
            "histogram_counts": np.histogram(col, bins=10)[0].tolist(),
            "histogram_edges":  np.histogram(col, bins=10)[1].tolist(),
        }
    stats["_predictions"] = {
        "mean": float(np.mean(predictions)),
        "std":  float(np.std(predictions)),
        "histogram_counts": np.histogram(predictions, bins=20,
                                          range=(0, 1))[0].tolist(),
    }
    stats["_saved_at"] = time.time()
    TRAINING_STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    TRAINING_STATS_PATH.write_text(json.dumps(stats, indent=2))
    logger.info(f"Training stats saved for {len(feature_names)} features")


def compute_psi(expected: np.ndarray, actual: np.ndarray, n_bins: int = 10) -> float:
    """
    PSI = Σ_i (act_pct - exp_pct) * ln(act_pct / exp_pct)
    Uses training data percentiles as bin edges (not equal-width bins).
    Laplace smoothing prevents log(0).
    """
    if len(expected) == 0 or len(actual) == 0:
        return 0.0
        
    bin_edges = np.nanpercentile(expected, np.linspace(0, 100, n_bins + 1))
    bin_edges = np.unique(bin_edges)
    if len(bin_edges) < 2:
        return 0.0

    exp_counts = np.histogram(expected, bins=bin_edges)[0]
    act_counts = np.histogram(actual, bins=bin_edges)[0]

    eps = 0.5
    exp_pct = (exp_counts + eps) / (len(expected) + eps * (len(bin_edges) - 1))
    act_pct = (act_counts + eps) / (len(actual) + eps * (len(bin_edges) - 1))

    return float(np.sum((act_pct - exp_pct) * np.log(act_pct / exp_pct)))


def compute_ks(expected: np.ndarray, actual: np.ndarray) -> tuple[float, float]:
    """Two-sample KS test. Returns (statistic, p-value)."""
    if len(expected) == 0 or len(actual) == 0:
        return 0.0, 1.0
    stat, pval = scipy_stats.ks_2samp(expected, actual)
    return float(stat), float(pval)


def compute_jsd(p_train_hist: np.ndarray, p_current: np.ndarray) -> float:
    """
    Jensen-Shannon Divergence between prediction distributions.
    JSD(P||Q) = 0.5 * KL(P||M) + 0.5 * KL(Q||M)  where M = 0.5*(P+Q)
    Uses histogram approximation with 20 bins in [0,1].
    """
    if len(p_current) == 0 or p_train_hist.sum() == 0:
        return 0.0
        
    bins = np.linspace(0, 1, 21)
    
    p_hist = p_train_hist.astype(float)
    q_hist = np.histogram(p_current, bins=bins)[0].astype(float)
    
    if p_hist.sum() == 0 or q_hist.sum() == 0:
        return 0.0
        
    p_hist = p_hist + 1e-9
    q_hist = q_hist + 1e-9
    
    p_hist /= p_hist.sum()
    q_hist /= q_hist.sum()
    
    m = 0.5 * (p_hist + q_hist)
    kl_pm = np.sum(p_hist * np.log(p_hist / m))
    kl_qm = np.sum(q_hist * np.log(q_hist / m))
    return float(0.5 * (kl_pm + kl_qm))


def reconstruct_distribution_from_hist(counts: list, edges: list, n_samples: int = 1000) -> np.ndarray:
    """Reconstruct an approximate distribution from histogram counts and edges."""
    if sum(counts) == 0:
        return np.array([])
        
    probs = np.array(counts) / sum(counts)
    bin_indices = np.random.choice(len(counts), size=n_samples, p=probs)
    
    samples = []
    for idx in bin_indices:
        low = edges[idx]
        high = edges[idx+1]
        samples.append(np.random.uniform(low, high))
        
    return np.array(samples)


def check_drift(
    new_feature_data: pd.DataFrame,
    new_predictions: np.ndarray,
    feature_names: list
) -> dict:
    """
    Full drift report for all features + prediction distribution.
    Returns structured report with per-feature flags.
    
    Retraining recommended if:
      - Any feature PSI ≥ 0.25, OR
      - Any feature KS p-value < 0.01, OR
      - Prediction JSD > 0.10
    """
    if not TRAINING_STATS_PATH.exists():
        logger.warning("No training stats file — drift detection skipped")
        return {"retrain_recommended": False, "reason": "no_baseline"}

    baseline = json.loads(TRAINING_STATS_PATH.read_text())

    report = {
        "checked_at": time.time(),
        "n_new_samples": len(new_feature_data),
        "features": {},
        "prediction_jsd": None,
        "retrain_recommended": False,
        "retrain_reasons": [],
    }

    psi_threshold_retrain = DomainConstants.PSI_RETRAIN_THRESHOLD
    psi_threshold_monitor = DomainConstants.PSI_MONITOR_THRESHOLD
    ks_retrain_threshold = 0.01

    for feat in feature_names:
        if feat not in baseline or feat not in new_feature_data.columns:
            continue

        b = baseline[feat]
        
        # Reconstruct approximate training distribution from histogram
        train_vals = reconstruct_distribution_from_hist(
            b["histogram_counts"], 
            b["histogram_edges"], 
            n_samples=1000
        )
        
        new_vals = new_feature_data[feat].dropna().values

        if len(new_vals) < 10 or len(train_vals) < 10:
            continue

        psi = compute_psi(train_vals, new_vals)
        ks_stat, ks_pval = compute_ks(train_vals, new_vals)

        status = "STABLE"
        if psi >= psi_threshold_retrain or ks_pval < ks_retrain_threshold:
            status = "RETRAIN"
            report["retrain_recommended"] = True
            report["retrain_reasons"].append(
                f"{feat}: PSI={psi:.3f}, KS_p={ks_pval:.4f}"
            )
        elif psi >= psi_threshold_monitor:
            status = "MONITOR"

        report["features"][feat] = {
            "psi": round(psi, 4),
            "ks_statistic": round(ks_stat, 4),
            "ks_pvalue": round(ks_pval, 4),
            "status": status,
        }

    # Prediction distribution drift
    if "_predictions" in baseline and len(new_predictions) >= 10:
        b_pred = baseline["_predictions"]
        jsd = compute_jsd(
            np.array(b_pred["histogram_counts"]),
            new_predictions
        )
        report["prediction_jsd"] = round(jsd, 4)
        if jsd > 0.10:
            report["retrain_recommended"] = True
            report["retrain_reasons"].append(f"Prediction JSD={jsd:.3f} > 0.10")

    # Persist report to SQLite for audit trail
    _save_drift_report(report)

    n_retrain = sum(1 for f in report["features"].values() if f["status"] == "RETRAIN")
    n_monitor = sum(1 for f in report["features"].values() if f["status"] == "MONITOR")
    logger.info(
        f"Drift check: {n_retrain} retrain, {n_monitor} monitor, "
        f"JSD={report.get('prediction_jsd', 'N/A')}, "
        f"retrain_recommended={report['retrain_recommended']}"
    )
    return report


def _save_drift_report(report: dict):
    MONITORING_DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(MONITORING_DB)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS drift_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checked_at REAL,
            n_samples INTEGER,
            retrain_recommended INTEGER,
            reasons TEXT,
            jsd REAL,
            report_json TEXT
        )
    """)
    conn.execute(
        "INSERT INTO drift_reports VALUES (NULL,?,?,?,?,?,?)",
        (
            report["checked_at"],
            report["n_new_samples"],
            int(report["retrain_recommended"]),
            json.dumps(report["retrain_reasons"]),
            report.get("prediction_jsd"),
            json.dumps(report),
        )
    )
    conn.commit()
    conn.close()
