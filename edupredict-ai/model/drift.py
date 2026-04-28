import numpy as np
import pandas as pd
from config import DomainConstants

def compute_psi(expected: np.ndarray, 
                actual: np.ndarray, 
                n_bins: int = 10) -> float:
    """
    Population Stability Index:
        PSI = Σ_i (A_i - E_i) * ln(A_i / E_i)
    """
    if len(expected) == 0 or len(actual) == 0:
        return 0.0

    # Bin edges derived from expected distribution
    breakpoints = np.nanpercentile(expected, np.linspace(0, 100, n_bins + 1))
    breakpoints = np.unique(breakpoints)
    
    # If feature has low cardinality and collapses to a single bin
    if len(breakpoints) <= 1:
        return 0.0
        
    # We use len(breakpoints)-1 bins
    actual_n_bins = len(breakpoints) - 1
    
    expected_counts = np.histogram(expected, bins=breakpoints)[0]
    actual_counts = np.histogram(actual, bins=breakpoints)[0]
    
    # Laplace smoothing to avoid log(0)
    expected_pct = (expected_counts + 0.5) / (len(expected) + 0.5 * actual_n_bins)
    actual_pct = (actual_counts + 0.5) / (len(actual) + 0.5 * actual_n_bins)
    
    psi = np.sum((actual_pct - expected_pct) * np.log(actual_pct / expected_pct))
    return float(psi)

def drift_report(train_df: pd.DataFrame, 
                 new_df: pd.DataFrame,
                 feature_cols: list) -> pd.DataFrame:
    """Compute PSI for every feature. Flag features based on config thresholds."""
    records = []
    
    monitor_thresh = DomainConstants.PSI_MONITOR_THRESHOLD
    retrain_thresh = DomainConstants.PSI_RETRAIN_THRESHOLD
    
    for col in feature_cols:
        expected = train_df[col].dropna().values
        actual = new_df[col].dropna().values
        
        psi = compute_psi(expected, actual)
        
        status = "STABLE"
        if psi >= retrain_thresh:
            status = "RETRAIN"
        elif psi >= monitor_thresh:
            status = "MONITOR"
            
        records.append({
            "feature": col,
            "psi": round(psi, 4),
            "status": status
        })
    return pd.DataFrame(records).sort_values("psi", ascending=False)
