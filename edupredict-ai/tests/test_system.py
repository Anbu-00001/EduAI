import pytest
import numpy as np
import sys, os, time, json
import pandas as pd
from fastapi.testclient import TestClient

# Add project to path
sys.path.append(os.getcwd())

from app.api.main import app
from model.conformal import ConformalPredictor
from model.fairness import audit_fairness, apply_fairness_constraint
from model.drift import compute_psi
from model.loan_roi import compute_loan_roi
from model.skill_gap import generate_skill_gap_report
from config import EnvConfig, DomainConstants

client = TestClient(app)

def test_config_resolution():
    assert EnvConfig.DATABASE_URL() is not None

def test_api_health():
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": "5.0.0"}

def test_conformal_empty_data():
    cp = ConformalPredictor(alpha=0.10)
    with pytest.raises(Exception):
        cp.calibrate(np.array([]), np.array([]))

def test_fairness_audit_robustness():
    # Test with valid groups
    df = pd.DataFrame({
        "repaid_loan": [1, 1, 0, 0, 1, 0],
        "gender": ["M", "M", "F", "F", "F", "M"]
    })
    probs = np.array([0.9, 0.8, 0.2, 0.3, 0.85, 0.1])
    report = audit_fairness(df, probs, "gender")
    assert "demographic_parity_index" in report
    
    # Test apply_fairness_constraint
    _, thresholds = apply_fairness_constraint(probs, df["gender"].values, target_dpi=0.95)
    assert "M" in thresholds and "F" in thresholds

def test_drift_empty_data():
    # Empty data should not throw ZeroDivisionError
    ref = np.array([])
    curr = np.array([])
    psi = compute_psi(ref, curr)
    assert psi == 0.0

def test_loan_roi_math():
    roi = compute_loan_roi(
        field="computer_science",
        loan_amount_inr=1000000,
        annual_interest_rate=0.10,
        tenure_years=5,
        starting_salary_norm=0.8,
        repayment_probability=0.85
    )
    assert roi.loan_amount_inr == 1000000
    assert roi.tenure_months == 60
    assert roi.emi_inr > 0
    assert len(roi.salary_trajectory) == 5
    assert len(roi.emi_to_salary_ratios) == 5
    
    # 10L loan over 5 years at 10% is ~21247/mo -> ~254k/yr
    assert abs(roi.emi_inr - 21247) < 500 

def test_skill_gap_priority():
    features = np.zeros(13)
    feature_names = ["cgpa_normalized", "internships_count", "backlogs", "median_salary_normalized", "potential_score", "demand_proxy", "placement_rate_for_field", "demand_velocity_per_day", "demand_acceleration", "velocity_r_squared", "demand_momentum", "market_hhi", "macro_index"]
    
    cf_result = {
        "changes_required": {
            "cgpa_normalized": {"original": 0.6, "counterfactual": 0.8, "change": 0.2},
            "internships_count": {"original": 0, "counterfactual": 2, "change": 2}
        }
    }
    
    def dummy_predict(x):
        # simple mock
        p = 0.5
        if x[0][0] > 0.7: p += 0.15 # cgpa
        if x[0][1] > 1: p += 0.10  # internship
        return np.array([p])
    
    report = generate_skill_gap_report(
        features, cf_result, dummy_predict, feature_names, 0.5, "computer_science", 0.72
    )
    
    # Internships should probably be higher priority than CGPA due to effort scores
    assert len(report.actions) == 2
    assert report.actions[0].priority_score >= report.actions[1].priority_score
