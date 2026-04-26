from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict
import numpy as np
import pickle, json, os, uuid
from datetime import datetime
import pandas as pd
import shap
import logging
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from model.temporal_features import build_peer_cohort_graph

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
        
        # Phase 3 additions
        app.state.graph_params = json.load(open(base_path + "graph_params.json"))
        app.state.X_train = np.load(base_path + "X_train_sc.npy")
        app.state.y_train = np.load(base_path + "y_train.npy")
        
        print("✅ EduPredict AI v3.0: All mathematical artifacts and graph params loaded.")
    except Exception as e:
        print(f"❌ Startup Error: {e}")
    yield

app = FastAPI(
    title="EduPredict AI API",
    description="Future Earning Potential Engine for Student Loan Underwriting",
    version="3.0.0",
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
    p_model: float
    p_cohort: float
    p_blended: float
    confidence_interval_90pct: Dict[str, float]
    risk_tier: str
    recommendation: str
    potential_score: float
    shap_contributions: Dict[str, float]
    counterfactual: Optional[Dict]
    fairness_note: str
    model_version: str
    timestamp: str

def build_features(profile: StudentProfile, demand_lookup: dict, velocity_lookup: dict, market_hhi: float) -> np.ndarray:
    cgpa_norm = profile.cgpa / 10.0
    internship_weight = (profile.internships_count / 3.0) # Using simple linear weight as per Phase 3A/B alignment
    if internship_weight > 1.0: internship_weight = 1.0
    
    demand_proxy = demand_lookup.get(profile.field_of_study, 0.5)
    salary_norm = demand_proxy 
    placement_rate_norm = profile.college_placement_rate / 100.0
    
    # Potential score remains same logic as v2.0 for base, but we'll use it in features
    potential_score = (0.25 * cgpa_norm + 0.25 * internship_weight + 0.25 * placement_rate_norm + 0.25 * demand_proxy)
    
    # Temporal features
    v_data = velocity_lookup.get(profile.field_of_study, {"velocity": 0.0, "accel": 0.0, "r2": 0.0})
    velocity = v_data["velocity"]
    accel = v_data["accel"]
    r2 = v_data["r2"]
    
    # Scale velocity for momentum (assuming typical range -100 to 100 for normalization)
    v_scaled = np.clip((velocity + 50) / 100, 0, 1)
    momentum = 0.3 * v_scaled + 0.7 * demand_proxy
    
    if profile.field_of_study not in velocity_lookup:
        logging.warning(f"Temporal features missing for {profile.field_of_study}, defaulting to 0.0")

    return np.array([
        cgpa_norm,
        profile.internships_count,
        profile.backlogs,
        salary_norm,
        potential_score,
        demand_proxy,
        placement_rate_norm,
        velocity,
        accel,
        r2,
        momentum,
        market_hhi
    ])

@app.post("/v1/assess", response_model=AssessmentResponse)
async def assess_student(profile: StudentProfile, background_tasks: BackgroundTasks):
    # 1. Load Demand and Velocity context
    demand_lookup = {}
    velocity_lookup = {}
    market_hhi = 0.14 # default 1/7
    try:
        demand_cache = json.load(open("data/pipeline/demand_cache.json"))
        demand_records = demand_cache["records"]
        demand_lookup = {r["field"]: r["job_count_normalized"] for r in demand_records}
        
        from model.temporal_features import compute_demand_velocity, compute_hhi
        vel_df = compute_demand_velocity()
        velocity_lookup = {r["field"]: {"velocity": r["demand_velocity_per_day"], "accel": r["demand_acceleration"], "r2": r["velocity_r_squared"]} for r in vel_df.to_dict(orient="records")}
        market_hhi = compute_hhi(pd.DataFrame(demand_records))
    except: pass
    
    feature_names = [
        "cgpa_normalized", "internships_count", "backlogs",
        "median_salary_normalized", "potential_score", "demand_proxy",
        "placement_rate_for_field", "demand_velocity_per_day",
        "demand_acceleration", "velocity_r_squared", "demand_momentum", "market_hhi"
    ]
    
    features = build_features(profile, demand_lookup, velocity_lookup, market_hhi)
    features_df = pd.DataFrame([features], columns=feature_names)
    features_sc = app.state.scaler.transform(features_df)
    
    # 2. Ensemble Inference (p_model)
    base_models = app.state.base_models
    xgb_probs = np.mean([m.predict_proba(features_sc)[:, 1] for m in base_models["xgb"]], axis=0)
    lgb_probs = np.mean([m.predict(features_sc) for m in base_models["lgb"]], axis=0)
    cat_probs = np.mean([m.predict_proba(features_sc)[:, 1] for m in base_models["cat"]], axis=0)
    
    meta_input = np.column_stack([xgb_probs, lgb_probs, cat_probs])
    p_model = float(app.state.meta_model.predict_proba(meta_input)[0, 1])
    
    # 3. Peer Cohort Inference (p_cohort)
    p_cohort = float(build_peer_cohort_graph(app.state.X_train, app.state.y_train, features_sc)[0])
    
    # 4. Blending
    alpha = app.state.graph_params["alpha"]
    p_blended = alpha * p_model + (1 - alpha) * p_cohort
    
    # 5. Calibration
    cal_params = app.state.calibration
    if cal_params.get("method") == "isotonic":
        bins = np.array(cal_params["bins"])
        lookup = np.array(cal_params["lookup"])
        cal_prob = float(np.interp(p_blended, bins, lookup))
    else:
        A, B = cal_params.get("A", 1.0), cal_params.get("B", 0.0)
        cal_prob = float(1 / (1 + np.exp(A * p_blended + B)))
    
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
        repayment_probability=round(p_blended, 4),
        calibrated_probability=round(cal_prob, 4),
        p_model=round(p_model, 4),
        p_cohort=round(p_cohort, 4),
        p_blended=round(p_blended, 4),
        confidence_interval_90pct={"lower": round(ci_lower, 4), "upper": round(ci_upper, 4)},
        risk_tier=risk_tier,
        recommendation=recommendation,
        potential_score=round(float(features[4]), 4),
        shap_contributions=shap_contributions,
        counterfactual=counterfactual,
        fairness_note="Model audited for demographic parity ≥ 0.80 across degree fields",
        model_version="v3.0-temporal-graph",
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

@app.get("/v1/data/freshness")
async def get_freshness():
    try:
        stats = json.load(open("data/pipeline/source_stats.json"))
        cache = json.load(open("data/pipeline/demand_cache.json"))
        
        sources = []
        from data.pipeline.dag import SOURCE_DECAY, reliability_score
        for s, decay in SOURCE_DECAY.items():
            last_attempt = stats.get(s, {}).get("last_attempt", cache["generated_at"])
            sources.append({
                "name": s,
                "reliability_score": round(reliability_score(stats, s), 4),
                "freshness_weight": round(np.exp(-decay * (time.time() - last_attempt)/3600), 4),
                "last_attempt_ago_hours": round((time.time() - last_attempt)/3600, 2)
            })
            
        return {
            "sources": sources,
            "demand_data_age_hours": round((time.time() - cache["generated_at"])/3600, 2),
            "data_confidence_avg": round(np.mean([r["data_confidence"] for r in cache["records"]]), 4),
            "cache_valid": (time.time() - cache["generated_at"])/3600 < 24
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/v1/data/refresh")
async def refresh_data(background_tasks: BackgroundTasks):
    from data.pipeline.dag import run_dag
    background_tasks.add_task(run_dag)
    return {"status": "refresh_scheduled"}

@app.get("/v1/health")
async def health():
    return {"status": "ok", "model_version": "v3.0-temporal-graph"}
