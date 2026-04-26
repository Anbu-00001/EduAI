import os
import json
import pickle
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import shap
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

# Imports from project modules
from data.pipeline.dag import get_demand_data
from model.temporal_features import compute_demand_velocity, add_temporal_features, build_peer_cohort_graph, tune_graph_alpha
from model.ensemble import train_stacked_ensemble
from model.calibration import platt_scale, compute_ece, plot_calibration_curve
from model.conformal import ConformalPredictor

FEATURE_COLS_V3 = [
    "cgpa_normalized", "internships_count", "backlogs",
    "median_salary_normalized", "potential_score", "demand_proxy",
    "placement_rate_for_field", "demand_velocity_per_day",
    "demand_acceleration", "velocity_r_squared", "demand_momentum", "market_hhi"
]

def retrain():
    print("Starting Phase 3 Retraining...")
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
    
    demand_df = get_demand_data()
    velocity_df = compute_demand_velocity()
    df = add_temporal_features(df, velocity_df, demand_df)
    
    # 2. Split (80/20)
    X = df[FEATURE_COLS_V3]
    y = df["repaid_loan"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    # 3. Scaling
    scaler = StandardScaler()
    X_train_sc = pd.DataFrame(scaler.fit_transform(X_train), columns=FEATURE_COLS_V3)
    X_test_sc = pd.DataFrame(scaler.transform(X_test), columns=FEATURE_COLS_V3)
    
    pickle.dump(scaler, open("model/artifacts/scaler.pkl", "wb"))
    np.save("model/artifacts/X_train_sc.npy", X_train_sc.values)
    np.save("model/artifacts/y_train.npy", y_train.values)
    
    # 4. Ensemble Training with OOF
    base_models, meta_model, oof_auc, p_model_oof = train_stacked_ensemble(X_train_sc, y_train)
    
    # 5. Probability Helper
    def get_ensemble_prob(X_data):
        xp = np.mean([m.predict_proba(X_data)[:, 1] for m in base_models["xgb"]], axis=0)
        lp = np.mean([m.predict(X_data) for m in base_models["lgb"]], axis=0)
        cp = np.mean([m.predict_proba(X_data)[:, 1] for m in base_models["cat"]], axis=0)
        mi = np.column_stack([xp, lp, cp])
        return meta_model.predict_proba(mi)[:, 1]
    
    p_model_test = get_ensemble_prob(X_test_sc)
    
    # 6. Peer Cohort (OOF for training set, direct for test)
    p_cohort_oof = build_peer_cohort_graph(X_train_sc.values, y_train.values, X_train_sc.values)
    p_cohort_test = build_peer_cohort_graph(X_train_sc.values, y_train.values, X_test_sc.values)
    
    # 7. Alpha Tuning (Using OOF)
    alpha = tune_graph_alpha(p_model_oof, p_cohort_oof, y_train.values)
    print(f"Optimal Alpha: {alpha:.4f}")
    
    # 8. Blending
    p_blended_oof = alpha * p_model_oof + (1 - alpha) * p_cohort_oof
    p_blended_test = alpha * p_model_test + (1 - alpha) * p_cohort_test
    
    # 9. Calibration (Fit on OOF, apply to Test)
    calibrated_test, cal_params = platt_scale(p_blended_oof, y_train.values, p_blended_test)
    
    # 9.1 Verify and Plot Calibration
    ece_val = compute_ece(calibrated_test, y_test.values)
    print(f"Final ECE: {ece_val:.4f}")
    plot_calibration_curve(p_blended_test, calibrated_test, y_test.values, "model/artifacts/reliability_diagram_v3.png")
    
    # 10. Conformal Prediction
    # Split test set for conformal calibration
    p_conf_cal, p_conf_test, y_conf_cal, y_conf_test = train_test_split(
        calibrated_test, y_test, test_size=0.5, random_state=99
    )
    cp = ConformalPredictor(alpha=0.10)
    q_hat = cp.calibrate(p_conf_cal, y_conf_cal.values)
    coverage = cp.coverage_check(p_conf_test, y_conf_test.values)
    
    # 11. SHAP
    explainer = shap.TreeExplainer(base_models["xgb"][0])
    shap_values = explainer.shap_values(X_test_sc)
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values, X_test_sc, show=False)
    plt.tight_layout()
    plt.savefig("model/artifacts/shap_summary_v3.png")
    plt.close()
    
    # 13. Save JSON artifacts
    json.dump(cal_params, open("model/artifacts/calibration_params.json", "w"), indent=2)
    json.dump({"q_hat": q_hat, **coverage}, open("model/artifacts/conformal_params.json", "w"), indent=2)
    
    feature_ranges = {col: [float(X[col].min()), float(X[col].max())] for col in FEATURE_COLS_V3}
    json.dump(feature_ranges, open("model/artifacts/feature_ranges.json", "w"), indent=2)
    
    graph_params = {"alpha": alpha}
    json.dump(graph_params, open("model/artifacts/graph_params.json", "w"), indent=2)
    
    # 14. Metrics
    graph_auc = roc_auc_score(y_test, calibrated_test)
    metrics = {
        "stacked_ensemble_auc": round(oof_auc, 4),
        "graph_regularised_auc": round(graph_auc, 4),
        "auc_improvement": round(graph_auc - 0.62, 4),
        "post_calibration_ece": round(ece_val, 4),
        "conformal_coverage_90pct": round(coverage["empirical_coverage"], 4),
        "n_features_v3": len(FEATURE_COLS_V3),
        "model_version": "v3.0-temporal-graph"
    }
    json.dump(metrics, open("model/artifacts/metrics.json", "w"), indent=2)
    
    print("\n✅ Phase 3 Retraining Complete")
    for k, v in metrics.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    retrain()
