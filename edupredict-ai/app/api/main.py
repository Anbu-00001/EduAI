from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict
import numpy as np
import pickle, json, os, uuid
from datetime import datetime
import pandas as pd
import shap
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan manager: ensures model artifacts (weights, scalers, parameters)
    are loaded into memory before the API accepts traffic.
    
    Mathematics of the Load:
    - Stacked Meta-Model: Layer 2 Logistic Regression coefficients.
    - Base Learners: Ensembles of tree-based decision boundaries (H_i).
    - Calibration: Platt parameters (A, B) for sigmoid mapping.
    - Conformal: Non-conformity quantile (q_hat) for coverage guarantee.
    """
    base_path = "model/artifacts/"
    try:
        app.state.meta_model = pickle.load(open(base_path + "meta_model.pkl", "rb"))
        app.state.base_models = pickle.load(open(base_path + "base_models.pkl", "rb"))
        app.state.scaler = pickle.load(open(base_path + "scaler.pkl", "rb"))
        app.state.calibration = json.load(open(base_path + "calibration_params.json"))
        app.state.conformal_qhat = json.load(open(base_path + "conformal_params.json"))["q_hat"]
        app.state.feature_ranges = json.load(open(base_path + "feature_ranges.json"))
        app.state.metrics = json.load(open(base_path + "metrics.json"))
        print("✅ EduPredict AI: All mathematical artifacts loaded.")
    except Exception as e:
        print(f"❌ Startup Error: {e}")
    yield

app = FastAPI(
    title="EduPredict AI API",
    description="Future Earning Potential Engine for Student Loan Underwriting",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve Frontend
app.mount("/static", StaticFiles(directory="app/api/static"), name="static")

@app.get("/")
async def serve_home():
    return FileResponse("app/api/static/index.html")

class StudentProfile(BaseModel):
    cgpa: float = Field(..., ge=0.0, le=10.0)
    internships_count: int = Field(..., ge=0, le=10)
    backlogs: int = Field(..., ge=0, le=20)
    field_of_study: str = Field(...)
    college_placement_rate: float = Field(..., ge=0.0, le=100.0)
    loan_amount_inr: float = Field(..., ge=10000.0)
    annual_family_income_inr: Optional[float] = Field(None, ge=0)
    
    @field_validator("field_of_study")
    @classmethod
    def validate_field(cls, v):
        valid = ["computer_science", "data_science", "mba_finance",
                 "mechanical_engineering", "electrical_engineering",
                 "civil_engineering", "biotechnology"]
        if v not in valid:
            raise ValueError(f"field_of_study must be one of {valid}")
        return v

class AssessmentResponse(BaseModel):
    assessment_id: str
    repayment_probability: float
    calibrated_probability: float
    confidence_interval_90pct: Dict[str, float]
    risk_tier: str
    recommendation: str
    potential_score: float
    shap_contributions: Dict[str, float]
    counterfactual: Optional[Dict]
    fairness_note: str
    model_version: str
    timestamp: str

def build_features(profile: StudentProfile, demand_lookup: dict) -> np.ndarray:
    cgpa_norm = profile.cgpa / 10.0
    internship_weight = 1 - np.exp(-0.8 * profile.internships_count)
    demand_proxy = demand_lookup.get(profile.field_of_study, 0.5)
    # Using field demand as a proxy for salary normalization if specific data missing
    salary_norm = demand_proxy 
    placement_rate_norm = profile.college_placement_rate / 100.0
    # Non-linear interaction: Academic synergy with market demand
    # Formula: Score = (Base + Interaction) * Penalty
    # Interaction: log(1 + cgpa * demand) scales higher for top students in top fields
    synergy = np.log1p(cgpa_norm * demand_proxy)
    
    backlog_penalty = 1 / (1 + 0.3 * profile.backlogs)
    potential_score = (
        0.25 * cgpa_norm +
        0.20 * internship_weight +
        0.20 * placement_rate_norm +
        0.15 * synergy +
        0.10 * salary_norm +
        0.10 * demand_proxy
    ) * backlog_penalty
    
    return np.array([
        cgpa_norm,
        profile.internships_count,
        profile.backlogs,
        salary_norm,
        potential_score,
        demand_proxy,
        placement_rate_norm
    ])

@app.post("/v1/assess", response_model=AssessmentResponse)
async def assess_student(profile: StudentProfile, background_tasks: BackgroundTasks):
    demand_lookup = {}
    try:
        demand_df = pd.read_csv("data/raw/naukri_jobs_live.csv")
        demand_lookup = dict(zip(demand_df["field"], demand_df["demand_normalized"]))
    except: pass
    
    feature_names = ["cgpa_normalized", "internships_count", "backlogs",
                     "median_salary_normalized", "potential_score",
                     "demand_proxy", "placement_rate_for_field"]
    features = build_features(profile, demand_lookup)
    features_df = pd.DataFrame([features], columns=feature_names)
    features_sc = app.state.scaler.transform(features_df)
    
    base_models = app.state.base_models
    xgb_probs = np.mean([m.predict_proba(features_sc)[:, 1] for m in base_models["xgb"]], axis=0)
    lgb_probs = np.mean([m.predict(features_sc) for m in base_models["lgb"]], axis=0)
    cat_probs = np.mean([m.predict_proba(features_sc)[:, 1] for m in base_models["cat"]], axis=0)
    
    meta_input = np.column_stack([xgb_probs, lgb_probs, cat_probs])
    raw_prob = float(app.state.meta_model.predict_proba(meta_input)[0, 1])
    
    A, B = app.state.calibration["A"], app.state.calibration["B"]
    cal_prob = float(1 / (1 + np.exp(A * raw_prob + B)))
    
    q_hat = app.state.conformal_qhat
    ci_lower, ci_upper = max(0.0, cal_prob - q_hat), min(1.0, cal_prob + q_hat)
    
    risk_tier = "GREEN" if cal_prob >= 0.72 else "AMBER" if cal_prob >= 0.50 else "RED"
    recommendation = {
        "GREEN": "APPROVE — High earning trajectory confidence",
        "AMBER": "APPROVE WITH CONDITIONS — Quarterly review required",
        "RED": "DECLINE or require co-signer"
    }[risk_tier]
    
    best_xgb = base_models["xgb"][-1]
    explainer = shap.TreeExplainer(best_xgb)
    shap_vals = explainer.shap_values(features_sc)[0]
    feature_names = ["cgpa_normalized", "internships_count", "backlogs",
                     "median_salary_normalized", "potential_score",
                     "demand_proxy", "placement_rate_for_field"]
    shap_contributions = {name: round(float(val), 4) for name, val in zip(feature_names, shap_vals)}
    
    counterfactual = None
    if risk_tier in ["RED", "AMBER"]:
        from model.counterfactual import find_counterfactual
        def predict_fn(x):
            x_sc = app.state.scaler.transform(x)
            xp = np.mean([m.predict_proba(x_sc)[:, 1] for m in base_models["xgb"]], axis=0)
            lp = np.mean([m.predict(x_sc) for m in base_models["lgb"]], axis=0)
            cp = np.mean([m.predict_proba(x_sc)[:, 1] for m in base_models["cat"]], axis=0)
            mi = np.column_stack([xp, lp, cp])
            return app.state.meta_model.predict_proba(mi)[:, 1]
        
        cf_raw = find_counterfactual(features, predict_fn, feature_names, app.state.feature_ranges, target_prob=0.72)
        counterfactual = {
            "original_probability": float(cf_raw["original_probability"]),
            "counterfactual_probability": float(cf_raw["counterfactual_probability"]),
            "target_probability": float(cf_raw["target_probability"]),
            "achieved": bool(cf_raw["achieved"]),
            "changes_required": cf_raw["changes_required"],
            "num_features_changed": int(cf_raw["num_features_changed"])
        }
    
    return AssessmentResponse(
        assessment_id=str(uuid.uuid4()),
        repayment_probability=round(raw_prob, 4),
        calibrated_probability=round(cal_prob, 4),
        confidence_interval_90pct={"lower": round(ci_lower, 4), "upper": round(ci_upper, 4)},
        risk_tier=risk_tier,
        recommendation=recommendation,
        potential_score=round(float(features[4]), 4),
        shap_contributions=shap_contributions,
        counterfactual=counterfactual,
        fairness_note="Model audited for demographic parity ≥ 0.80 across degree fields",
        model_version="v2.0-stacked-ensemble",
        timestamp=datetime.utcnow().isoformat()
    )

@app.post("/v1/portfolio/simulate")
async def simulate_portfolio(profiles: List[StudentProfile], n_simulations: int = 10000):
    probs = []
    demand_lookup = {}
    try:
        demand_df = pd.read_csv("data/raw/naukri_jobs_live.csv")
        demand_lookup = dict(zip(demand_df["field"], demand_df["demand_normalized"]))
    except: pass

    feature_names = ["cgpa_normalized", "internships_count", "backlogs",
                     "median_salary_normalized", "potential_score",
                     "demand_proxy", "placement_rate_for_field"]
    for p in profiles:
        features = build_features(p, demand_lookup)
        features_df = pd.DataFrame([features], columns=feature_names)
        features_sc = app.state.scaler.transform(features_df)
        xp = np.mean([m.predict_proba(features_sc)[:, 1] for m in app.state.base_models["xgb"]], axis=0)[0]
        lp = np.mean([m.predict(features_sc) for m in app.state.base_models["lgb"]], axis=0)[0]
        cp = np.mean([m.predict_proba(features_sc)[:, 1] for m in app.state.base_models["cat"]], axis=0)[0]
        mi = np.column_stack([[xp], [lp], [cp]])
        raw_p = app.state.meta_model.predict_proba(mi)[0, 1]
        cal_p = 1 / (1 + np.exp(app.state.calibration["A"] * raw_p + app.state.calibration["B"]))
        probs.append(float(cal_p))
    
    probs = np.array(probs)
    default_probs = 1 - probs
    simulated_defaults = np.random.default_rng(42).binomial(1, default_probs, size=(n_simulations, len(probs)))
    portfolio_default_rates = simulated_defaults.mean(axis=1)
    
    expected_loss = float(portfolio_default_rates.mean())
    var_95 = float(np.percentile(portfolio_default_rates, 95))
    cvar_95 = float(portfolio_default_rates[portfolio_default_rates >= var_95].mean())
    
    return {
        "portfolio_size": len(profiles),
        "expected_loss_rate": round(expected_loss, 4),
        "var_95": round(var_95, 4),
        "cvar_95": round(cvar_95, 4),
        "prob_default_rate_above_20pct": float((portfolio_default_rates > 0.20).mean()),
        "average_repayment_probability": round(float(probs.mean()), 4)
    }

@app.get("/v1/health")
async def health():
    return {"status": "ok", "model_version": "v2.0-stacked-ensemble"}
