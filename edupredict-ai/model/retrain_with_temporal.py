import os
import json
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import shap
import logging
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

# Phase 4 Imports
from data.pipeline.dag import get_demand_data
from model.temporal_features import compute_demand_velocity, add_temporal_features, build_peer_cohort_graph, tune_graph_alpha, compute_macro_index
from model.ensemble import train_stacked_ensemble
from model.calibration import select_best_calibrator, compute_ece, plot_reliability_diagram
from model.conformal import ConformalPredictor
from model.mlflow_tracking import log_training_run, register_model
from model.monitoring import save_training_stats
from model.fairness import audit_fairness
from model.generate_model_card import generate_model_card

logger = logging.getLogger(__name__)

FEATURE_COLS_V4 = [
    "cgpa_normalized", "internships_count", "backlogs",
    "median_salary_normalized", "potential_score", "demand_proxy",
    "placement_rate_for_field", "demand_velocity_per_day",
    "demand_acceleration", "velocity_r_squared", "demand_momentum", 
    "market_hhi", "macro_index"
]

def retrain():
    print("🚀 Starting Phase 4: Production Grade Retraining Pipeline...")
    os.makedirs("model/artifacts", exist_ok=True)
    
    # 1. Load and Augment Data
    features_path = "data/processed/features.csv"
    if not os.path.exists(features_path):
        from model.feature_engineering import build_master_dataset
        df = build_master_dataset("data/raw")
    else:
        df = pd.read_csv(features_path)
    
    if "field" not in df.columns:
        from data.pipeline.dag import FIELD_QUERIES
        fields = list(FIELD_QUERIES.keys())
        df["field"] = np.random.choice(fields, len(df))
    
    # Macro Index
    macro_idx = compute_macro_index(os.environ.get("DATAGOV_API_KEY", ""))
    df["macro_index"] = macro_idx
    
    # Temporal features
    demand_df = get_demand_data()
    velocity_df = compute_demand_velocity()
    df = add_temporal_features(df, velocity_df, demand_df)
    
    # 2. Split (75/25 for larger cal set as requested)
    X = df[FEATURE_COLS_V4]
    y = df["repaid_loan"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
    
    # 3. Scaling
    scaler = StandardScaler()
    X_train_sc = pd.DataFrame(scaler.fit_transform(X_train), columns=FEATURE_COLS_V4)
    X_test_sc = pd.DataFrame(scaler.transform(X_test), columns=FEATURE_COLS_V4)
    
    pickle.dump(scaler, open("model/artifacts/scaler.pkl", "wb"))
    np.save("model/artifacts/X_train_sc.npy", X_train_sc.values)
    np.save("model/artifacts/y_train.npy", y_train.values)
    
    # 4. Ensemble Training
    base_models, meta_model, oof_auc, p_model_oof = train_stacked_ensemble(X_train_sc, y_train)
    
    def get_ensemble_prob(X_data):
        xp = np.mean([m.predict_proba(X_data)[:, 1] for m in base_models["xgb"]], axis=0)
        lp = np.mean([m.predict(X_data) for m in base_models["lgb"]], axis=0)
        cp = np.mean([m.predict_proba(X_data)[:, 1] for m in base_models["cat"]], axis=0)
        mi = np.column_stack([xp, lp, cp])
        return meta_model.predict_proba(mi)[:, 1]
    
    p_model_test = get_ensemble_prob(X_test_sc)
    
    # 5. Graph Regularisation
    p_cohort_oof = build_peer_cohort_graph(X_train_sc.values, y_train.values, X_train_sc.values)
    p_cohort_test = build_peer_cohort_graph(X_train_sc.values, y_train.values, X_test_sc.values)
    alpha = tune_graph_alpha(p_model_oof, p_cohort_oof, y_train.values)
    p_blended_oof = alpha * p_model_oof + (1 - alpha) * p_cohort_oof
    p_blended_test = alpha * p_model_test + (1 - alpha) * p_cohort_test
    
    # 6. Isotonic Calibration (using 25% of OOF for calibration selection)
    p_cal_train, p_cal_val, y_cal_train, y_cal_val = train_test_split(
        p_blended_oof, y_train.values, test_size=0.25, random_state=42
    )
    calibrator, method_name, val_ece = select_best_calibrator(p_cal_train, y_cal_train, p_cal_val, y_cal_val)
    
    if method_name == "isotonic":
        calibrated_test = calibrator.predict(p_blended_test)
        cal_params = {"method": "isotonic", "bins": calibrator.X_thresholds_.tolist(), "lookup": calibrator.y_thresholds_.tolist()}
    else:
        A, B = calibrator["A"], calibrator["B"]
        calibrated_test = 1 / (1 + np.exp(A * p_blended_test + B))
        cal_params = calibrator

    ece_pre = compute_ece(p_blended_test, y_test.values)
    ece_post = compute_ece(calibrated_test, y_test.values)
    plot_reliability_diagram(p_blended_test, calibrated_test, y_test.values, method_name, "model/artifacts/reliability_v4.png")
    
    # 7. Conformal Prediction
    cp = ConformalPredictor(alpha=0.10)
    q_hat = cp.calibrate(calibrated_test[:len(calibrated_test)//2], y_test.values[:len(calibrated_test)//2])
    coverage = cp.coverage_check(calibrated_test[len(calibrated_test)//2:], y_test.values[len(calibrated_test)//2:])
    
    # 8. Fairness & SHAP
    fairness_report = audit_fairness(df.loc[X_test.index], calibrated_test, "field")
    explainer = shap.TreeExplainer(base_models["xgb"][0])
    shap_vals = explainer.shap_values(X_test_sc)
    
    # 9. Save Artifacts
    json.dump(cal_params, open("model/artifacts/calibration_params.json", "w"), indent=2)
    json.dump({"q_hat": q_hat, **coverage}, open("model/artifacts/conformal_params.json", "w"), indent=2)
    json.dump(fairness_report, open("model/artifacts/fairness_report.json", "w"), indent=2)
    feature_ranges = {col: [float(X[col].min()), float(X[col].max())] for col in FEATURE_COLS_V4}
    json.dump(feature_ranges, open("model/artifacts/feature_ranges.json", "w"), indent=2)
    json.dump({"alpha": alpha}, open("model/artifacts/graph_params.json", "w"), indent=2)
    
    metrics = {
        "stacked_ensemble_auc": round(oof_auc, 4),
        "graph_regularised_auc": round(roc_auc_score(y_test, calibrated_test), 4),
        "auc_improvement": round(roc_auc_score(y_test, calibrated_test) - 0.62, 4),
        "baseline_cibil_auc": 0.62,
        "pre_calibration_ece": round(ece_pre, 4),
        "post_calibration_ece": round(ece_post, 4),
        "conformal_q_hat": round(q_hat, 4),
        "train_size": len(X_train),
        "n_features_v4": len(FEATURE_COLS_V4),
        "model_version": "v4.0-production"
    }
    json.dump(metrics, open("model/artifacts/metrics.json", "w"), indent=2)
    
    # 10. Monitoring Stats & MLflow
    save_training_stats(X_train_sc.values, FEATURE_COLS_V4, p_blended_oof)
    
    run_id = log_training_run(
        metrics, base_models, meta_model, scaler, calibrator, method_name,
        alpha, FEATURE_COLS_V4, {"q_hat": q_hat, **coverage}, fairness_report
    )
    register_model(run_id)
    
    # 11. Model Card
    generate_model_card()
    
    print("\n✅ Phase 4 Retraining Complete")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    retrain()
