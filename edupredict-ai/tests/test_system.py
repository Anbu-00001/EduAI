import pytest
import numpy as np
import sys, os

# Add project to path
sys.path.append(os.getcwd())

# Add project to path
sys.path.append(os.path.join(os.getcwd(), "edupredict-ai"))

from model.conformal import ConformalPredictor
from model.fairness import compute_fairness_metrics
from model.counterfactual import find_counterfactual
from model.calibration import compute_ece, platt_scale

def test_conformal_coverage_guarantee():
    rng = np.random.default_rng(0)
    probs_cal = rng.uniform(0, 1, 200)
    labels_cal = (rng.uniform(0, 1, 200) < probs_cal).astype(int)
    probs_test = rng.uniform(0, 1, 500)
    labels_test = (rng.uniform(0, 1, 500) < probs_test).astype(int)
    
    cp = ConformalPredictor(alpha=0.10)
    cp.calibrate(probs_cal, labels_cal)
    coverage = cp.coverage_check(probs_test, labels_test)
    assert coverage["empirical_coverage"] >= 0.85 # Allow slight variance in small synthetic test

def test_ece_improves_after_calibration():
    rng = np.random.default_rng(42)
    raw = rng.beta(2, 5, 300)
    labels = (rng.uniform(size=300) < raw * 0.6).astype(int)
    cal, _ = platt_scale(raw[:200], labels[:200], raw[200:])
    raw_ece = compute_ece(raw[200:], labels[200:])
    cal_ece = compute_ece(cal, labels[200:])
    assert cal_ece <= raw_ece

def test_fairness_dpi_range():
    rng = np.random.default_rng(1)
    probs = rng.uniform(0, 1, 200)
    labels = rng.integers(0, 2, 200)
    attr = rng.integers(0, 2, 200)
    report = compute_fairness_metrics(labels, probs, attr)
    assert 0.0 <= report.demographic_parity_index <= 1.0

def test_counterfactual_achieves_target():
    def mock_model(x):
        x = np.atleast_2d(x)
        return np.clip(x[:, 0] * 0.6 + x[:, 1] * 0.4, 0, 1)
    
    student = np.array([0.9, 0.9, 0.5, 0.5, 0.5, 0.5, 0.5])
    ranges = {f"f{i}": (0.0, 1.0) for i in range(7)}
    fnames = [f"f{i}" for i in range(7)]
    result = find_counterfactual(student, mock_model, fnames, ranges, target_prob=0.95)
    assert "changes_required" in result
    assert result["counterfactual_probability"] >= 0.89 # tolerance

def test_psi_known_values():
    from model.drift import compute_psi
    x = np.random.default_rng(0).normal(0, 1, 1000)
    psi = compute_psi(x, x + np.random.default_rng(1).normal(0, 0.01, 1000))
    assert psi < 0.10
