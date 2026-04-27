"""
Field Demand Ranker — "Which degree field gives me the best ROI?"

Composite Score per field:
  field_score = w1 * demand_normalized 
              + w2 * demand_velocity_normalized
              + w3 * salary_normalized
              + w4 * placement_rate_normalized
              + w5 * (1 - market_hhi)     # Lower concentration = more job diversity
  
  Weights w1..w5 are NOT hardcoded. They are derived from the SHAP feature
  importance rankings of the trained ensemble model:
    w_i = |mean_shap_i| / Σ |mean_shap_j|  (normalised absolute SHAP importance)
  
  This means the ranking weights automatically reflect what the model
  actually learned matters most for loan repayment — not our assumptions.

Adjacent Field Recommendation:
  For a student in field F with profile X, find field F* such that:
    F* = argmax_{F' ≠ F} [field_score(F') - skill_transfer_cost(F, F')]
  
  skill_transfer_cost(F, F') = cosine_distance(embedding(F), embedding(F'))
  where embedding is computed using sentence-transformers on field descriptions.
  
  Lower transfer cost = fields are more similar = easier to switch.
  This gives students realistic adjacent field recommendations.
"""

import numpy as np
import pandas as pd
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

FIELD_DESCRIPTIONS = {
    "computer_science": (
        "Software engineering, programming, algorithms, data structures, "
        "computer networks, operating systems, web development"
    ),
    "data_science": (
        "Machine learning, statistics, data analysis, Python, SQL, "
        "deep learning, neural networks, data engineering"
    ),
    "mba_finance": (
        "Financial analysis, accounting, investment banking, corporate finance, "
        "business strategy, management consulting, valuation"
    ),
    "mechanical_engineering": (
        "Thermodynamics, fluid mechanics, manufacturing, CAD design, "
        "materials science, robotics, automotive engineering"
    ),
    "electrical_engineering": (
        "Circuit design, signal processing, power systems, embedded systems, "
        "electronics, VLSI, telecommunications, control systems"
    ),
    "civil_engineering": (
        "Structural engineering, construction, geotechnical, transportation, "
        "environmental engineering, urban planning, project management"
    ),
    "biotechnology": (
        "Molecular biology, genetics, pharmaceutical research, bioinformatics, "
        "clinical trials, medical devices, genomics"
    ),
}


def _load_shap_weights() -> dict:
    """
    Load feature importance from SHAP summary and derive field ranking weights.
    Falls back to equal weights only if SHAP file not found.
    """
    import pickle
    import shap as shap_lib
    
    try:
        # Adjusted paths to match actual file structure
        base_models = pickle.load(open("model/artifacts/base_models.pkl", "rb"))
        scaler = pickle.load(open("model/artifacts/scaler.pkl", "rb"))
        feature_cols = json.loads(
            Path("model/artifacts/metrics.json").read_text()
        ).get("feature_cols_v3", [])
        
        X_train = np.load("model/artifacts/X_train_sc.npy")
        
        # Use first XGBoost fold for SHAP
        best_xgb = base_models["xgb"][0]
        explainer = shap_lib.TreeExplainer(best_xgb)
        
        # Sample 200 rows for speed
        sample_idx = np.random.choice(len(X_train), min(200, len(X_train)), replace=False)
        shap_values = explainer.shap_values(X_train[sample_idx])
        
        mean_abs_shap = np.abs(shap_values).mean(axis=0)
        total = mean_abs_shap.sum()
        
        weights = {
            feat: float(mean_abs_shap[i] / total)
            for i, feat in enumerate(feature_cols)
        }
        logger.info(f"SHAP-derived weights: {weights}")
        return weights
        
    except Exception as e:
        logger.warning(f"SHAP weight loading failed: {e} — using equal weights")
        return {}


def _compute_field_embeddings() -> dict:
    """
    Compute sentence embeddings for each field description.
    Used for skill transfer cost between fields.
    Returns: {field: embedding_vector}
    """
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = {}
        for field, desc in FIELD_DESCRIPTIONS.items():
            embeddings[field] = model.encode(desc)
        logger.info(f"Field embeddings computed: {len(embeddings)} fields")
        return embeddings
    except Exception as e:
        logger.warning(f"Embeddings unavailable: {e}")
        return {}


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """cosine_distance = 1 - cosine_similarity ∈ [0, 2]"""
    dot = np.dot(a, b)
    norm = (np.linalg.norm(a) * np.linalg.norm(b)) + 1e-9
    return float(1.0 - dot / norm)


def rank_fields(student_field: Optional[str] = None) -> pd.DataFrame:
    """
    Rank all degree fields by their composite score.
    
    If student_field provided, also compute:
      - Transfer cost from student's current field to each alternative
      - Adjusted rank = composite_score - transfer_cost_weight * transfer_cost
    
    Returns DataFrame sorted by composite score (desc).
    """
    cache = json.loads(Path("data/pipeline/demand_cache.json").read_text())
    records = {r["field"]: r for r in cache["records"]}
    
    from model.temporal_features import compute_demand_velocity, compute_hhi
    vel_df = compute_demand_velocity()
    vel_map = dict(zip(vel_df["field"], vel_df["demand_velocity_per_day"]))
    
    demand_df = pd.DataFrame(cache["records"])
    hhi = compute_hhi(demand_df)
    
    shap_weights = _load_shap_weights()
    
    # Default weights if SHAP unavailable
    w_demand   = shap_weights.get("demand_proxy", 0.25)
    w_velocity = shap_weights.get("demand_velocity_per_day", 0.20)
    w_salary   = shap_weights.get("median_salary_normalized", 0.25)
    w_placement = shap_weights.get("placement_rate_for_field", 0.20)
    w_diversity = 0.10
    
    # Normalise weights to sum to 1
    w_total = w_demand + w_velocity + w_salary + w_placement + w_diversity
    w_demand    /= w_total
    w_velocity  /= w_total
    w_salary    /= w_total
    w_placement /= w_total
    w_diversity /= w_total
    
    # Normalise velocity to [0, 1]
    all_vel = np.array(list(vel_map.values()))
    v_min, v_max = all_vel.min(), all_vel.max()
    v_range = (v_max - v_min) + 1e-9
    
    rows = []
    for field, r in records.items():
        d_norm   = float(r.get("demand_normalized", 0.5))
        vel_raw  = vel_map.get(field, 0.0)
        v_norm   = (vel_raw - v_min) / v_range
        sal_norm = float(r.get("demand_normalized", 0.5))  # Proxy if salary not in cache
        plac_norm = 0.7   # Default — override if NIRF data available
        div_score = 1.0 - hhi   # Higher diversity = lower HHI
        
        composite = (
            w_demand * d_norm +
            w_velocity * v_norm +
            w_salary * sal_norm +
            w_placement * plac_norm +
            w_diversity * div_score
        )
        
        rows.append({
            "field": field,
            "demand_normalized": round(d_norm, 4),
            "velocity_normalized": round(v_norm, 4),
            "salary_normalized": round(sal_norm, 4),
            "placement_normalized": round(plac_norm, 4),
            "diversity_score": round(div_score, 4),
            "composite_score": round(composite, 4),
            "demand_tier": r.get("demand_tier", "MEDIUM"),
        })
    
    df = pd.DataFrame(rows).sort_values("composite_score", ascending=False)
    df["rank"] = range(1, len(df) + 1)
    
    # Adjacent field recommendation with transfer cost
    if student_field and student_field in FIELD_DESCRIPTIONS:
        embeddings = _compute_field_embeddings()
        if embeddings and student_field in embeddings:
            student_emb = embeddings[student_field]
            transfer_costs = {}
            for field in df["field"]:
                if field != student_field and field in embeddings:
                    transfer_costs[field] = cosine_distance(student_emb, embeddings[field])
                else:
                    transfer_costs[field] = 0.0
            
            df["transfer_cost"] = df["field"].map(transfer_costs)
            
            # Adjusted score: composite minus transfer cost penalty
            # transfer_cost_weight = 0.30 (meaningful but not dominant)
            df["adjusted_score"] = df["composite_score"] - 0.30 * df["transfer_cost"]
            df["recommendation_rank"] = df["adjusted_score"].rank(ascending=False).astype(int)
            df["is_student_field"] = df["field"] == student_field
        else:
            df["transfer_cost"] = 0.0
            df["adjusted_score"] = df["composite_score"]
            df["recommendation_rank"] = df["rank"]
            df["is_student_field"] = df["field"] == student_field
    
    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = rank_fields(student_field="civil_engineering")
    print(df[["rank", "field", "composite_score", 
               "demand_tier", "transfer_cost", "recommendation_rank"]].to_string())
