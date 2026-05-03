import pytest
import numpy as np
import sys, os, time, json
import pandas as pd
from fastapi.testclient import TestClient

# Add project to path
sys.path.append(os.getcwd())

from app.api.main import app, StudentProfile
from model.conformal import ConformalPredictor
from model.fairness import audit_fairness, apply_fairness_constraint
from model.drift import compute_psi
from model.loan_roi import compute_loan_roi
from model.skill_gap import generate_skill_gap_report
from config import EnvConfig, DomainConstants

from app.api.auth import get_current_tenant
from unittest.mock import MagicMock
app.dependency_overrides[get_current_tenant] = lambda: {"tenant_id": "demo_lender", "rate_limit_rpm": 1000}
app.state.metrics = {}
app.state.demand_lookup = {}
app.state.velocity_lookup = {}
app.state.market_hhi = 0.143
app.state.macro_index = 0.72
app.state.scaler = MagicMock()
app.state.meta_model = MagicMock()
app.state.base_models = {"xgb": [MagicMock()], "lgb": [MagicMock()], "cat": [MagicMock()]}
app.state.calibration = {"method": "isotonic", "bins": [0, 1], "lookup": [0, 1]}
app.state.conformal_qhat = 0.1
app.state.feature_ranges = {}
app.state.X_train = np.random.rand(10, 14)
app.state.y_train = np.random.randint(0, 2, 10)
app.state.graph_params = {"alpha": 0.5}
app.state.db_pool = MagicMock()

import app.api.main as main_module
main_module.build_peer_cohort_graph = MagicMock(return_value=np.array([0.8]))
main_module.select_best_calibrator = MagicMock(return_value=(MagicMock(), "isotonic", 0.01))

import shap
shap.TreeExplainer = MagicMock()

client = TestClient(app)

def test_config_resolution():
    assert EnvConfig.DATABASE_URL() is not None

def test_api_health():
    response = client.get("/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "5.0.0"
    assert "model_version" in data
    assert "model_auc" in data

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
    features = np.zeros(14)
    feature_names = ["cgpa_normalized", "internships_count", "backlogs", "median_salary_normalized", "potential_score", "demand_proxy", "placement_rate_for_field", "demand_velocity_per_day", "demand_acceleration", "velocity_r_squared", "demand_momentum", "market_hhi", "macro_index", "backlogs_missing"]
    
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
    assert len(report.actions) >= 2
    assert report.actions[0].priority_score >= report.actions[1].priority_score

def test_phase_5_bug_fixes():
    # Bug 1: salary_norm NIRF lookup
    from model.data_builder import get_nirf_salary_norm
    # CS median 8.5L -> norm ~0.34
    # Civil median 4.2L -> norm ~0.10
    norm_cs = get_nirf_salary_norm("computer_science")
    norm_civil = get_nirf_salary_norm("civil_engineering")
    assert norm_cs > norm_civil, "CS salary norm should be higher than Civil"

    # Bug 2: backlogs_missing presence
    from model.feature_pipeline import FeaturePipeline, TemporalFeatures, MarketFeatures
    f_cs = FeaturePipeline.transform(
        cgpa=8.0, internships_count=1, backlogs=0, field_of_study="computer_science", 
        college_placement_rate=80, salary_norm=norm_cs, 
        temporal=TemporalFeatures(), market=MarketFeatures()
    )
    assert len(f_cs) == 14, "Feature vector must have 14 elements (V5)"
    assert f_cs[13] == 0, "backlogs_missing should be 0 for standard inference"

    # Bug 3: loan_amount_inr upper bound
    response = client.post("/v1/assess", json={
        "cgpa": 8.0, "internships_count": 1, "backlogs": 0,
        "field_of_study": "computer_science", "college_placement_rate": 80,
        "loan_amount_inr": 6000000, "user_hash": "test"
    })
    assert response.status_code == 422 # Pydantic validation error

    # Bug 4: user_hash mandatory
    response = client.post("/v1/assess", json={
        "cgpa": 8.0, "internships_count": 1, "backlogs": 0,
        "field_of_study": "computer_science", "college_placement_rate": 80,
        "loan_amount_inr": 500000
    })
    assert response.status_code == 422 # Mandatory check

    # Bug 5: CORS wildcard fix
    from config import EnvConfig
    origins = EnvConfig.ALLOWED_ORIGINS()
    assert "*" not in origins, "CORS should not use wildcard in Phase 5"

    # Bug 6: safe_load_artifact integrity
    from model.data_builder import safe_load_artifact
    import tempfile, pickle, os
    from pathlib import Path
    with tempfile.NamedTemporaryFile(suffix=".pkl", delete=False) as tmp:
        pickle.dump({"dummy": "data"}, tmp)
        tmp_name = tmp.name
    
    try:
        with pytest.raises(RuntimeError):
            # Pass a wrong hash
            safe_load_artifact(tmp_name, {Path(tmp_name).name: "wrong_hash"})
    finally:
        if os.path.exists(tmp_name):
            os.remove(tmp_name)
