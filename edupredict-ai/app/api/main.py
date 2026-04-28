from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Security, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict
import numpy as np
import pickle, json, os, uuid, time
from datetime import datetime
import pandas as pd
import shap
import logging
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
from dataclasses import asdict

# Phase 5 Imports
from model.loan_roi import compute_loan_roi, LoanROIReport
from model.field_ranker import rank_fields
from model.skill_gap import generate_skill_gap_report
from model.college_roi import score_college
from model.data_builder import safe_load_artifact, get_nirf_salary_norm

# Prometheus
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_client import Counter, Histogram, Gauge

# Phase 4 Modules
from app.api.auth import get_current_tenant
from app.api.rate_limit import check_rate_limit
from app.api.consent import check_consent, get_consent_notice
from model.temporal_features import build_peer_cohort_graph, compute_macro_index
from model.scheduler import create_scheduler

from config import EnvConfig

logger = logging.getLogger(__name__)

# Custom metrics
PREDICTION_COUNTER = Counter(
    "edupredict_predictions_total",
    "Total loan assessments",
    ["risk_tier", "field_of_study", "tenant_id"]
)
PREDICTION_PROBABILITY = Histogram(
    "edupredict_calibrated_probability",
    "Distribution of calibrated repayment probabilities",
    buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)
ECE_GAUGE = Gauge("edupredict_current_ece", "Current model Expected Calibration Error")
AUC_GAUGE = Gauge("edupredict_current_auc", "Current model graph-regularised AUC")
FAIRNESS_DPI_GAUGE = Gauge("edupredict_fairness_dpi", "Current demographic parity index")
DAG_FRESHNESS_GAUGE = Gauge("edupredict_demand_cache_age_hours", "Age of demand cache in hours")
DRIFT_PSI_GAUGE = Gauge("edupredict_max_feature_psi", "Maximum PSI across all features")

ADVERSE_ACTION_CODES = {
    "cgpa_normalized":           "AA-01: Academic performance below threshold",
    "backlogs":                  "AA-02: Academic backlogs indicate risk",
    "internships_count":         "AA-03: Insufficient work experience",
    "demand_proxy":              "AA-04: Low market demand in selected field",
    "placement_rate_for_field":  "AA-05: Institution placement rate below benchmark",
    "median_salary_normalized":  "AA-06: Projected salary insufficient for loan amount",
    "potential_score":           "AA-07: Overall potential score below threshold",
    "demand_velocity_per_day":   "AA-08: Field demand trending downward",
    "market_hhi":                "AA-09: Highly concentrated job market increases risk",
    "macro_index":               "AA-10: Unfavorable macroeconomic conditions",
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager: loads models, starts scheduler, initializes DB pool."""
    import asyncpg
    from app.api.auth import hash_api_key
    
    app.state.db_pool = await asyncpg.create_pool(EnvConfig.DATABASE_URL())
    
    # Initialize Demo Tenant & API Key for Dashboard
    async with app.state.db_pool.acquire() as conn:
        # Initialize Demo Tenant (API Key should be seeded via script/DB directly)
        # Removing hardcoded key seeding for Phase 5 security
        pass
    
    base_path = "model/artifacts/"
    try:
        hashes = json.load(open(base_path + "artifact_hashes.json"))
        app.state.meta_model = safe_load_artifact(base_path + "meta_model.pkl", hashes)
        app.state.base_models = safe_load_artifact(base_path + "base_models.pkl", hashes)
        app.state.scaler = safe_load_artifact(base_path + "scaler.pkl", hashes)
        app.state.calibration = json.load(open(base_path + "calibration_params.json"))
        app.state.conformal_qhat = json.load(open(base_path + "conformal_params.json"))["q_hat"]
        app.state.feature_ranges = json.load(open(base_path + "feature_ranges.json"))
        metrics = json.load(open(base_path + "metrics.json"))
        app.state.metrics = metrics
        app.state.graph_params = json.load(open(base_path + "graph_params.json"))
        app.state.X_train = np.load(base_path + "X_train_sc.npy")
        app.state.y_train = np.load(base_path + "y_train.npy")
        
        # Set gauges
        ECE_GAUGE.set(metrics.get("post_calibration_ece", 0))
        AUC_GAUGE.set(metrics.get("graph_regularised_auc", 0))
        
        logger.info("✅ EduPredict AI v5.0: Production artifacts and Monitoring active.")
    except Exception as e:
        logger.error(f"❌ Startup Error: {e}")

    # Start Scheduler
    app.state.scheduler = create_scheduler()
    app.state.scheduler.start()
    
    yield
    
    app.state.scheduler.shutdown()
    await app.state.db_pool.close()

app = FastAPI(
    title="EduPredict AI API",
    description="Production-Grade Student Loan Risk Engine",
    version="5.0.0",
    lifespan=lifespan
)

Instrumentator().instrument(app).expose(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=EnvConfig.ALLOWED_ORIGINS().split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    user_hash: Optional[str] = Field(None, validate_default=True) # For DPDP consent check
    
    @field_validator("field_of_study")
    @classmethod
    def validate_field(cls, v):
        from config import FIELD_QUERIES
        valid = list(FIELD_QUERIES.keys())
        if v not in valid:
            raise ValueError(f"field_of_study must be one of {valid}")
        return v

    @field_validator("loan_amount_inr")
    @classmethod
    def validate_loan(cls, v):
        if v > 5_000_000:
            raise ValueError("loan_amount_inr capped at ₹50,00,000 for advisory mode")
        return v

    @field_validator("user_hash")
    @classmethod
    def validate_consent(cls, v):
        if not v:
            raise ValueError("user_hash (DPDP Consent) is mandatory for v5.0 assess")
        return v

class ConsentRequest(BaseModel):
    user_hash: str
    consent_given: bool
    data_sources: List[str]

@app.post("/v1/consent")
async def record_user_consent(req: ConsentRequest, request: Request):
    from app.api.consent import record_consent
    consent_id = await record_consent(
        request.app.state.db_pool,
        req.user_hash,
        req.consent_given,
        request.client.host,
        request.headers.get("user-agent", ""),
        req.data_sources
    )
    return {"consent_id": consent_id, "status": "recorded"}

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
    adverse_action: Optional[Dict]
    fairness_note: str
    model_version: str
    timestamp: str

def build_features(profile: StudentProfile, demand_lookup: dict, velocity_lookup: dict, market_hhi: float, macro_index: float) -> np.ndarray:
    cgpa_norm = profile.cgpa / 10.0
    internship_weight = min(profile.internships_count / 3.0, 1.0)
    demand_proxy = demand_lookup.get(profile.field_of_study, 0.5)
    salary_norm = get_nirf_salary_norm(profile.field_of_study)
    placement_rate_norm = profile.college_placement_rate / 100.0
    potential_score = (0.35 * cgpa_norm + 0.25 * internship_weight + 0.25 * placement_rate_norm + 0.15 * salary_norm)
    v_data = velocity_lookup.get(profile.field_of_study, {"velocity": 0.0, "accel": 0.0, "r2": 0.0})
    v_scaled = np.clip((v_data["velocity"] + 50) / 100, 0, 1)
    
    # Using EWMA alpha
    from model.temporal_features import _ewma_alpha
    alpha = _ewma_alpha(2.0)
    momentum = alpha * v_scaled + (1 - alpha) * demand_proxy
    
    return np.array([
        cgpa_norm, profile.internships_count, profile.backlogs,
        salary_norm, potential_score, demand_proxy,
        placement_rate_norm, v_data["velocity"], v_data["accel"],
        v_data["r2"], momentum, market_hhi, macro_index, 0
    ])

def generate_adverse_action_notice(shap_contributions: dict, risk_tier: str) -> Optional[dict]:
    if risk_tier != "RED": return None
    negative_shap = {k: v for k, v in shap_contributions.items() if v < 0}
    top_reasons = sorted(negative_shap.items(), key=lambda x: x[1])[:3]
    return {
        "adverse_action_required": True,
        "reasons": [{"code": ADVERSE_ACTION_CODES.get(f, f"AA-99: {f}"), "feature": f, "impact": round(v, 4)} for f, v in top_reasons],
        "notice": "Application declined based on factors listed. You have the right to dispute or request a free copy.",
        "rbi_reference": "RBI FREE-AI Framework, August 2025"
    }

async def log_api_call(db_pool, assessment_id, features_json, prediction, risk_tier, tenant_id):
    async with db_pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO api_calls (assessment_id, features_json, prediction, risk_tier, api_key_id)
            VALUES ($1, $2, $3, $4, $5)
        """, assessment_id, features_json, prediction, risk_tier, tenant_id)

@app.post("/v1/assess", response_model=AssessmentResponse)
async def assess_student(profile: StudentProfile, background_tasks: BackgroundTasks, request: Request, tenant: dict = Depends(get_current_tenant)):
    # 0. Rate Limit & Consent Check
    await check_rate_limit(tenant["tenant_id"], tenant["rate_limit_rpm"], request)
    if profile.user_hash:
        if not await check_consent(request.app.state.db_pool, profile.user_hash):
            raise HTTPException(status_code=403, detail="DPDP Consent missing or withdrawn")

    # 1. Context Loading
    demand_lookup, velocity_lookup, market_hhi = {}, {}, 0.14
    try:
        cache = json.load(open("data/pipeline/demand_cache.json"))
        demand_lookup = {r["field"]: r["job_count_normalized"] for r in cache["records"]}
        from model.temporal_features import compute_demand_velocity, compute_hhi
        vel_df = compute_demand_velocity()
        velocity_lookup = {r["field"]: {"velocity": r["demand_velocity_per_day"], "accel": r["demand_acceleration"], "r2": r["velocity_r_squared"]} for r in vel_df.to_dict(orient="records")}
        market_hhi = compute_hhi(pd.DataFrame(cache["records"]))
    except Exception as e:
        logger.warning(f"Failed to load temporal context: {e}")
    
    macro_index = compute_macro_index()
    
    feature_names = app.state.metrics.get("feature_cols_v3", [
        "cgpa_normalized", "internships_count", "backlogs", "median_salary_normalized",
        "potential_score", "demand_proxy", "placement_rate_for_field", "demand_velocity_per_day",
        "demand_acceleration", "velocity_r_squared", "demand_momentum", "market_hhi", "macro_index", "backlogs_missing"
    ])
    
    features = build_features(profile, demand_lookup, velocity_lookup, market_hhi, macro_index)
    features_sc = app.state.scaler.transform(pd.DataFrame([features], columns=feature_names))
    
    # 2. Ensemble & Graph Inference
    base_models = app.state.base_models
    xgb_p = np.mean([m.predict_proba(features_sc)[:, 1] for m in base_models["xgb"]], axis=0)
    lgb_p = np.mean([m.predict(features_sc) for m in base_models["lgb"]], axis=0)
    cat_p = np.mean([m.predict_proba(features_sc)[:, 1] for m in base_models["cat"]], axis=0)
    p_model = float(app.state.meta_model.predict_proba(np.column_stack([xgb_p, lgb_p, cat_p]))[0, 1])
    p_cohort = float(build_peer_cohort_graph(app.state.X_train, app.state.y_train, features_sc)[0])
    
    p_blended = app.state.graph_params["alpha"] * p_model + (1 - app.state.graph_params["alpha"]) * p_cohort
    
    # 3. Calibration & Conformal
    cal_params = app.state.calibration
    if cal_params.get("method") == "isotonic":
        bins = np.array(cal_params["bins"])
        lookup = np.array(cal_params["lookup"])
        idx = np.searchsorted(bins, p_blended, side="right") - 1
        idx = max(0, min(idx, len(lookup) - 1))
        cal_prob = float(lookup[idx])
    else:
        cal_prob = float(1 / (1 + np.exp(cal_params.get("A", 1.0) * p_blended + cal_params.get("B", 0.0))))
    
    q_hat = app.state.conformal_qhat
    ci = {"lower": round(max(0, cal_prob - q_hat), 4), "upper": round(min(1, cal_prob + q_hat), 4)}
    
    risk_tier = "GREEN" if cal_prob >= 0.72 else "AMBER" if cal_prob >= 0.50 else "RED"
    
    # 4. SHAP & Adverse Action
    explainer = shap.TreeExplainer(base_models["xgb"][-1])
    shap_vals = explainer.shap_values(features_sc)[0]
    shap_contributions = {n: round(float(v), 4) for n, v in zip(feature_names, shap_vals)}
    adverse_action = generate_adverse_action_notice(shap_contributions, risk_tier)
    
    # 5. Monitoring & Logging
    assessment_id = str(uuid.uuid4())
    PREDICTION_COUNTER.labels(risk_tier, profile.field_of_study, tenant["tenant_id"]).inc()
    PREDICTION_PROBABILITY.observe(cal_prob)
    background_tasks.add_task(log_api_call, app.state.db_pool, assessment_id, json.dumps(dict(zip(feature_names, features.tolist()))), cal_prob, risk_tier, tenant["tenant_id"])
    
    recommendations = {
        "GREEN": "High repayment probability. Profile exhibits strong academic and market indicators. Approved for preferential interest rates.",
        "AMBER": "Moderate risk. Repayment probability meets baseline requirements but warrants additional collateral or co-signer verification.",
        "RED": "High risk detected. Model suggests significant variance in earning potential. Application requires manual underwriter review."
    }
    
    return AssessmentResponse(
        assessment_id=assessment_id,
        repayment_probability=round(p_blended, 4),
        calibrated_probability=round(cal_prob, 4),
        p_model=round(p_model, 4), p_cohort=round(p_cohort, 4), p_blended=round(p_blended, 4),
        confidence_interval_90pct=ci, risk_tier=risk_tier,
        recommendation=recommendations.get(risk_tier, "Decision pending"),
        potential_score=round(features[4], 4),
        shap_contributions=shap_contributions, counterfactual=None, adverse_action=adverse_action,
        fairness_note="Audited for DPDP compliance and demographic parity",
        model_version=app.state.metrics.get("model_version", "unknown"), timestamp=datetime.utcnow().isoformat()
    )

@app.post("/v1/shadow/assess")
async def shadow_assess(profile: StudentProfile, request: Request, existing_score: float = 0.0, tenant: dict = Depends(get_current_tenant)):
    result = await assess_student(profile, BackgroundTasks(), request, tenant)
    agreement = "AGREE" if (result.calibrated_probability >= 0.5) == (existing_score >= 0.5) else "DISAGREE"
    return {
        "shadow_result": result, "existing_system_score": existing_score,
        "score_delta": round(result.calibrated_probability - existing_score, 4),
        "agreement": agreement, "note": "Shadow mode — for validation only"
    }

@app.get("/v1/consent/notice")
async def get_notice():
    return get_consent_notice()

@app.post("/v1/student/loan-roi")
async def student_loan_roi(
    profile: StudentProfile,
    request: Request,
    annual_interest_rate: float = 0.105,   # 10.5% — typical NBFC rate
    tenure_years: int = 7,
    tenant: dict = Depends(get_current_tenant)
):
    """
    Student-facing: "Is this loan worth taking?"
    Returns full ROI analysis including 5-year salary trajectory,
    EMI-to-salary ratios, break-even year, and NPV.
    No DPDP consent required — student is querying about themselves.
    """
    demand_lookup, velocity_lookup, market_hhi = {}, {}, 0.14
    try:
        cache = json.load(open("data/pipeline/demand_cache.json"))
        demand_lookup = {r["field"]: r["job_count_normalized"] for r in cache["records"]}
        from model.temporal_features import compute_demand_velocity, compute_hhi
        vel_df = compute_demand_velocity()
        velocity_lookup = {r["field"]: {"velocity": r["demand_velocity_per_day"], "accel": r["demand_acceleration"], "r2": r["velocity_r_squared"]} for r in vel_df.to_dict(orient="records")}
        market_hhi = compute_hhi(pd.DataFrame(cache["records"]))
    except Exception as e:
        logger.warning(f"Failed to load temporal context: {e}")
    
    macro_index = compute_macro_index()
    starting_salary_norm = demand_lookup.get(profile.field_of_study, 0.5)
    
    # Get repayment probability (reuses existing assessment logic)
    feature_names = app.state.metrics.get("feature_cols_v3", [])
    features = build_features(profile, demand_lookup, velocity_lookup, market_hhi, macro_index)
    features_sc = app.state.scaler.transform(
        pd.DataFrame([features], columns=feature_names)
    )
    base_models = app.state.base_models
    xp = np.mean([m.predict_proba(features_sc)[:, 1] for m in base_models["xgb"]], axis=0)
    lp = np.mean([m.predict(features_sc) for m in base_models["lgb"]], axis=0)
    cp = np.mean([m.predict_proba(features_sc)[:, 1] for m in base_models["cat"]], axis=0)
    mi = np.column_stack([xp, lp, cp])
    p_model = float(app.state.meta_model.predict_proba(mi)[0, 1])
    
    p_cohort = float(build_peer_cohort_graph(app.state.X_train, app.state.y_train, features_sc)[0])
    p_blended = app.state.graph_params["alpha"] * p_model + (1 - app.state.graph_params["alpha"]) * p_cohort
    
    cal_params = app.state.calibration
    if cal_params.get("method") == "isotonic":
        bins = np.array(cal_params["bins"])
        lookup = np.array(cal_params["lookup"])
        idx = np.searchsorted(bins, p_blended, side="right") - 1
        idx = max(0, min(idx, len(lookup) - 1))
        cal_prob = float(lookup[idx])
    else:
        cal_prob = float(1 / (1 + np.exp(cal_params["A"] * p_blended + cal_params["B"])))
    
    roi_report = compute_loan_roi(
        field=profile.field_of_study,
        loan_amount_inr=profile.loan_amount_inr,
        annual_interest_rate=annual_interest_rate,
        tenure_years=tenure_years,
        starting_salary_norm=starting_salary_norm,
        repayment_probability=cal_prob,
    )
    
    return {
        "repayment_probability": round(cal_prob, 4),
        "roi_analysis": asdict(roi_report),
        "summary": (
            f"With {cal_prob:.0%} repayment probability and "
            f"{roi_report.investment_verdict} investment verdict, "
            f"your EMI will be {roi_report.emi_to_salary_ratios[0]:.0%} "
            f"of Year-1 salary."
        )
    }


@app.get("/v1/student/field-ranking")
async def student_field_ranking(
    current_field: Optional[str] = None,
    tenant: dict = Depends(get_current_tenant)
):
    """
    Student-facing: "Which field has best job prospects?"
    Returns ranked fields with composite score, velocity, and
    transfer cost from student's current field.
    """
    df = rank_fields(student_field=current_field)
    return {
        "rankings": df.to_dict(orient="records"),
        "methodology": (
            "Fields ranked by SHAP-weighted composite of "
            "live job demand, demand velocity, salary proxy, "
            "placement rate, and market diversity (HHI)."
        ),
        "weights_source": "Derived from trained ensemble SHAP values — "
            "reflects what actually predicts loan repayment"
    }


@app.post("/v1/student/skill-gap")
async def student_skill_gap(
    profile: StudentProfile,
    request: Request,
    tenant: dict = Depends(get_current_tenant)
):
    """
    Student-facing: "What do I need to change to get approved?"
    Returns prioritised action roadmap with probability lifts per action.
    """
    demand_lookup, velocity_lookup, market_hhi = {}, {}, 0.14
    try:
        cache = json.load(open("data/pipeline/demand_cache.json"))
        demand_lookup = {r["field"]: r["job_count_normalized"] for r in cache["records"]}
        from model.temporal_features import compute_demand_velocity, compute_hhi
        vel_df = compute_demand_velocity()
        velocity_lookup = {r["field"]: {"velocity": r["demand_velocity_per_day"], "accel": r["demand_acceleration"], "r2": r["velocity_r_squared"]} for r in vel_df.to_dict(orient="records")}
        market_hhi = compute_hhi(pd.DataFrame(cache["records"]))
    except Exception as e:
        logger.warning(f"Failed to load temporal context: {e}")
    
    macro_index = compute_macro_index()
    feature_names = app.state.metrics.get("feature_cols_v3", [])
    features = build_features(profile, demand_lookup, velocity_lookup, market_hhi, macro_index)
    features_sc = app.state.scaler.transform(
        pd.DataFrame([features], columns=feature_names)
    )
    
    base_models = app.state.base_models
    def predict_fn(x):
        x_sc = app.state.scaler.transform(pd.DataFrame(x, columns=feature_names))
        xp = np.mean([m.predict_proba(x_sc)[:,1] for m in base_models["xgb"]], axis=0)
        lp = np.mean([m.predict(x_sc) for m in base_models["lgb"]], axis=0)
        cp = np.mean([m.predict_proba(x_sc)[:,1] for m in base_models["cat"]], axis=0)
        mi = np.column_stack([xp, lp, cp])
        p_mod = app.state.meta_model.predict_proba(mi)[:,1]
        
        # Need to include cohort prob for correct blended prob
        p_coh = build_peer_cohort_graph(app.state.X_train, app.state.y_train, x_sc)
        p_blend = app.state.graph_params["alpha"] * p_mod + (1 - app.state.graph_params["alpha"]) * p_coh
        
        cal_params = app.state.calibration
        if cal_params.get("method") == "isotonic":
            bins = np.array(cal_params["bins"])
            lookup = np.array(cal_params["lookup"])
            # searchsorted works on 1D arrays, p_blend could be 1D
            indices = np.searchsorted(bins, p_blend, side="right") - 1
            indices = np.clip(indices, 0, len(lookup) - 1)
            cal_p = lookup[indices]
        else:
            cal_p = 1 / (1 + np.exp(cal_params["A"] * p_blend + cal_params["B"]))
        return cal_p
    
    cal_prob = predict_fn(np.array([features]))[0]
    
    from model.counterfactual import find_counterfactual
    cf = find_counterfactual(
        features, predict_fn, feature_names,
        app.state.feature_ranges, target_prob=0.72
    )
    
    gap_report = generate_skill_gap_report(
        student_features=features,
        counterfactual_result=cf,
        predict_fn=predict_fn,
        feature_names=feature_names,
        current_probability=float(cal_prob),
        field=profile.field_of_study,
    )
    
    return {
        "current_probability": gap_report.current_probability,
        "current_tier": gap_report.current_tier,
        "target_tier": "GREEN",
        "estimated_time_to_green_months": gap_report.estimated_time_to_green_months,
        "priority_actions": [
            {
                "rank": i + 1,
                "feature": a.feature,
                "action": a.action_text,
                "probability_lift": a.probability_lift,
                "effort_score": a.effort_score,
                "priority_score": a.priority_score,
                "time_months": a.time_months,
                "feasibility": a.feasibility,
                "resources": a.resources,
            }
            for i, a in enumerate(gap_report.actions)
        ],
        "cumulative_probability_trajectory": gap_report.cumulative_lifts,
    }


@app.post("/v1/student/college-roi")
async def student_college_roi(
    college_name: str,
    field: str,
    placement_rate_pct: float,     # 0–100
    annual_tuition_inr: float,
    loan_amount_inr: float,
    annual_interest_rate: float = 0.105,
    tenure_years: int = 7,
    tenant: dict = Depends(get_current_tenant)
):
    """
    Student-facing: "Is this specific college worth the loan?"
    Returns ROI index, debt trap flag, and verdict.
    """
    result = score_college(
        college_name=college_name,
        field=field,
        placement_rate=placement_rate_pct / 100.0,
        annual_tuition_inr=annual_tuition_inr,
        loan_amount_inr=loan_amount_inr,
        annual_interest_rate=annual_interest_rate,
        tenure_years=tenure_years,
    )
    return asdict(result)


@app.get("/v1/health")
async def health():
    return {"status": "ok", "version": "5.0.0"}
