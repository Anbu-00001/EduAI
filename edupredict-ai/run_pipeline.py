"""
EduPredict AI — Full pipeline runner
Executes: scraping → feature engineering → ensemble training → 
          calibration → conformal → fairness audit → artifact export
"""
import subprocess, sys, json, time, os
import pandas as pd
import numpy as np
import pickle

def run_step(name: str, fn):
    print(f"\n{'='*60}")
    print(f"RUNNING: {name}")
    print('='*60)
    start = time.time()
    try:
        result = fn()
        elapsed = time.time() - start
        print(f"DONE: {name} ({elapsed:.1f}s)")
        return result
    except Exception as e:
        print(f"FAILED: {name} - {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def step_scrape():
    from scrapers.naukri_scraper import NaukriJobScraper
    scraper = NaukriJobScraper()
    df = scraper.build_demand_table()
    assert len(df) >= 3, "Need at least 3 fields scraped"
    return df

def step_features():
    from model.feature_engineering import build_master_dataset
    # Force run feature engineering
    df = build_master_dataset("edupredict-ai/data/raw")
    assert df.shape[0] >= 500, f"Expected ≥500 samples, got {df.shape[0]}"
    assert "repaid_loan" in df.columns
    assert df["repaid_loan"].nunique() == 2
    return df

def step_ensemble(df):
    from model.ensemble import train_stacked_ensemble
    from sklearn.preprocessing import StandardScaler
    import os
    
    FEATURE_COLS = ["cgpa_normalized", "internships_count", "backlogs",
                    "median_salary_normalized", "potential_score",
                    "demand_proxy", "placement_rate_for_field"]
    
    X = df[FEATURE_COLS]
    y = df["repaid_loan"]
    
    scaler = StandardScaler()
    X_sc = pd.DataFrame(scaler.fit_transform(X), columns=FEATURE_COLS)
    os.makedirs("edupredict-ai/model/artifacts", exist_ok=True)
    pickle.dump(scaler, open("edupredict-ai/model/artifacts/scaler.pkl", "wb"))
    
    # Save feature ranges for counterfactual
    feature_ranges = {col: [float(X[col].min()), float(X[col].max())] 
                      for col in FEATURE_COLS}
    json.dump(feature_ranges, open("edupredict-ai/model/artifacts/feature_ranges.json", "w"), indent=2)
    
    base_models, meta_model, oof_auc = train_stacked_ensemble(X_sc, y)
    return base_models, meta_model, X_sc, y, oof_auc, scaler

def step_calibrate(base_models, meta_model, X, y):
    from sklearn.model_selection import train_test_split
    from model.calibration import platt_scale, compute_ece, plot_calibration_curve
    
    # Use 20% as calibration set (separate from test set)
    X_cal, X_test, y_cal, y_test = train_test_split(X, y, test_size=0.2, 
                                                      random_state=123, stratify=y)
    
    def get_ensemble_prob(X_data):
        xp = np.mean([m.predict_proba(X_data)[:, 1] for m in base_models["xgb"]], axis=0)
        lp = np.mean([m.predict(X_data) for m in base_models["lgb"]], axis=0)
        cp = np.mean([m.predict_proba(X_data)[:, 1] for m in base_models["cat"]], axis=0)
        mi = np.column_stack([xp, lp, cp])
        return meta_model.predict_proba(mi)[:, 1]
    
    cal_probs = get_ensemble_prob(X_cal)
    test_probs = get_ensemble_prob(X_test)
    
    calibrated_test, cal_params = platt_scale(cal_probs, y_cal.values, test_probs)
    
    raw_ece = compute_ece(test_probs, y_test.values)
    cal_ece = compute_ece(calibrated_test, y_test.values)
    
    print(f"ECE before calibration: {raw_ece:.4f}")
    print(f"ECE after calibration:  {cal_ece:.4f}")
    
    plot_calibration_curve(test_probs, calibrated_test, y_test.values,
                           "edupredict-ai/model/artifacts/calibration_curve.png")
    
    json.dump(cal_params, open("edupredict-ai/model/artifacts/calibration_params.json", "w"))
    
    return calibrated_test, y_test, test_probs, raw_ece, cal_ece

def step_conformal(calibrated_probs, y_test):
    from model.conformal import ConformalPredictor
    from sklearn.model_selection import train_test_split
    
    # Further split test into conformal calibration + final test
    probs_conf, probs_final, y_conf, y_final = train_test_split(
        calibrated_probs, y_test, test_size=0.5, random_state=99
    )
    
    cp = ConformalPredictor(alpha=0.10)
    q_hat = cp.calibrate(probs_conf, y_conf.values)
    coverage = cp.coverage_check(probs_final, y_final.values)
    
    print(f"Conformal q_hat: {q_hat:.4f}")
    print(f"Coverage report: {coverage}")
    
    json.dump({"q_hat": q_hat, **coverage}, 
              open("edupredict-ai/model/artifacts/conformal_params.json", "w"), indent=2)
    
    return coverage

def step_fairness(base_models, meta_model, X, y):
    from model.fairness import compute_fairness_metrics
    
    # Use demand_proxy as sensitive attribute proxy
    demand_proxy = X["demand_proxy"]
    median_demand = demand_proxy.median()
    sensitive_attr = (demand_proxy >= median_demand).astype(int).values
    
    xp = np.mean([m.predict_proba(X)[:, 1] for m in base_models["xgb"]], axis=0)
    lp = np.mean([m.predict(X) for m in base_models["lgb"]], axis=0)
    cp = np.mean([m.predict_proba(X)[:, 1] for m in base_models["cat"]], axis=0)
    mi = np.column_stack([xp, lp, cp])
    probs = meta_model.predict_proba(mi)[:, 1]
    
    report = compute_fairness_metrics(y.values, probs, sensitive_attr)
    print(f"\nFairness Audit:\n{report}")
    
    fairness_dict = {
        "demographic_parity_index": report.demographic_parity_index,
        "equalized_odds_tpr_diff": report.equalized_odds_tpr_diff,
        "equalized_odds_fpr_diff": report.equalized_odds_fpr_diff,
        "predictive_parity_diff": report.predictive_parity_diff,
        "overall_fair": report.overall_fair
    }
    json.dump(fairness_dict, open("edupredict-ai/model/artifacts/fairness_report.json", "w"), indent=2)
    return report

def step_final_metrics(oof_auc, raw_ece, cal_ece, coverage, fairness_report):
    metrics = {
        "stacked_ensemble_auc": round(oof_auc, 4),
        "baseline_auc_cibil_only": 0.62,
        "auc_improvement": round(oof_auc - 0.62, 4),
        "pre_calibration_ece": round(raw_ece, 4),
        "post_calibration_ece": round(cal_ece, 4),
        "conformal_q_hat": coverage["q_hat"],
        "empirical_coverage_90pct": coverage["empirical_coverage"],
        "conformal_avg_interval_width": coverage["avg_interval_width"],
        "fairness_dpi": fairness_report.demographic_parity_index,
        "fairness_overall": fairness_report.overall_fair,
        "model_version": "v2.0-stacked-ensemble"
    }
    json.dump(metrics, open("edupredict-ai/model/artifacts/metrics.json", "w"), indent=2)
    
    print(f"\n{'='*60}")
    print("FINAL METRICS SUMMARY")
    print('='*60)
    for k, v in metrics.items():
        print(f"  {k}: {v}")
    print('='*60)
    return metrics

if __name__ == "__main__":
    # Ensure current directory is in path
    sys.path.append(os.path.join(os.getcwd(), "edupredict-ai"))
    
    demand_df    = run_step("1. Live Naukri scraping",   step_scrape)
    feature_df   = run_step("2. Feature engineering",    step_features)
    base, meta, X_sc, y, oof_auc, scaler = run_step("3. Stacked ensemble", 
                                                       lambda: step_ensemble(feature_df))
    cal_probs, y_test, raw_probs, raw_ece, cal_ece = run_step(
        "4. Platt calibration", lambda: step_calibrate(base, meta, X_sc, y))
    coverage     = run_step("5. Conformal prediction",   
                             lambda: step_conformal(cal_probs, y_test))
    fairness     = run_step("6. Fairness audit",         
                             lambda: step_fairness(base, meta, X_sc, y))
    metrics      = run_step("7. Metrics export",         
                             lambda: step_final_metrics(oof_auc, raw_ece, 
                                                        cal_ece, coverage, fairness))
    
    print("\n✅ Pipeline complete. Run: cd edupredict-ai && docker-compose up -d")
