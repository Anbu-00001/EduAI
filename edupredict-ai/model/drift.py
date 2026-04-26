import numpy as np
import pandas as pd

def compute_psi(expected: np.ndarray, 
                actual: np.ndarray, 
                n_bins: int = 10) -> float:
    """
    Population Stability Index:
        PSI = Σ_i (A_i - E_i) * ln(A_i / E_i)
    """
    # Bin edges derived from expected distribution
    breakpoints = np.nanpercentile(expected, np.linspace(0, 100, n_bins + 1))
    breakpoints = np.unique(breakpoints)
    
    expected_counts = np.histogram(expected, bins=breakpoints)[0]
    actual_counts = np.histogram(actual, bins=breakpoints)[0]
    
    # Laplace smoothing to avoid log(0)
    expected_pct = (expected_counts + 0.5) / (len(expected) + 0.5 * n_bins)
    actual_pct = (actual_counts + 0.5) / (len(actual) + 0.5 * n_bins)
    
    psi = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
    return float(psi)

def drift_report(train_df: pd.DataFrame, 
                 new_df: pd.DataFrame,
                 feature_cols: list) -> pd.DataFrame:
    """Compute PSI for every feature. Flag features with PSI ≥ 0.10."""
    records = []
    for col in feature_cols:
        psi = compute_psi(train_df[col].dropna().values, 
                          new_df[col].dropna().values)
        records.append({
            "feature": col,
            "psi": round(psi, 4),
            "status": "STABLE" if psi < 0.10 else 
                      "MONITOR" if psi < 0.25 else "RETRAIN"
        })
    return pd.DataFrame(records).sort_values("psi", ascending=False)
