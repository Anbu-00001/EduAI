import pytest
import numpy as np
import sys, os, time, json
import pandas as pd

# Add project to path
sys.path.append(os.getcwd())

from model.conformal import ConformalPredictor
from model.fairness import audit_fairness
from model.calibration import compute_ece, platt_calibrate, isotonic_calibrate, select_best_calibrator

def test_conformal_coverage_guarantee():
    rng = np.random.default_rng(0)
    probs_cal = rng.uniform(0, 1, 200)
    labels_cal = (rng.uniform(0, 1, 200) < probs_cal).astype(int)
    probs_test = rng.uniform(0, 1, 500)
    labels_test = (rng.uniform(0, 1, 500) < probs_test).astype(int)
    
    cp = ConformalPredictor(alpha=0.10)
    cp.calibrate(probs_cal, labels_cal)
    coverage = cp.coverage_check(probs_test, labels_test)
    assert coverage["empirical_coverage"] >= 0.85 # Allow slight variance

def test_calibration_selection():
    rng = np.random.default_rng(42)
    raw_cal = rng.beta(2, 5, 200)
    y_cal = (rng.uniform(size=200) < raw_cal * 0.7).astype(int)
    raw_val = rng.beta(2, 5, 100)
    y_val = (rng.uniform(size=100) < raw_val * 0.7).astype(int)
    
    calibrator, method, ece = select_best_calibrator(raw_cal, y_cal, raw_val, y_val)
    assert method in ["platt", "isotonic"]
    assert ece >= 0.0

def test_fairness_audit_structure():
    df = pd.DataFrame({
        "repaid_loan": np.random.randint(0, 2, 100),
        "field": np.random.choice(["A", "B"], 100)
    })
    probs = np.random.uniform(0, 1, 100)
    report = audit_fairness(df, probs, "field")
    assert "demographic_parity_index" in report
    assert "group_metrics" in report
    assert len(report["group_metrics"]) == 2

def test_macro_index_default():
    from model.temporal_features import compute_macro_index
    idx = compute_macro_index("invalid_key")
    assert 0.0 <= idx <= 1.0

def test_api_log_structure():
    # Verify monitoring DB tables are created
    from model.monitoring import _save_drift_report
    import sqlite3
    report = {
        "checked_at": time.time(),
        "n_new_samples": 10,
        "retrain_recommended": 0,
        "retrain_reasons": [],
        "jsd": 0.05
    }
    _save_drift_report(report)
    conn = sqlite3.connect("data/monitoring.db")
    res = conn.execute("SELECT count(*) FROM drift_reports").fetchone()
    assert res[0] > 0
    conn.close()
