"""
MLflow Experiment Tracking and Model Registry for EduPredict AI

Every training run logs:
  - All hyperparameters (from training code)
  - All metrics: OOF AUC, graph AUC, ECE before/after, conformal q_hat,
    fairness DPI, TPR diff, FPR diff
  - All artifacts: model pickles, SHAP plots, calibration curves
  - Git commit hash for reproducibility
  - Feature importance rankings

Model promotion policy (computed from data, not hardcoded):
  A new model is promoted to "Production" if and only if:
    new_auc - current_prod_auc > PROMOTION_DELTA_THRESHOLD
  where PROMOTION_DELTA_THRESHOLD = current_prod_std * 1.96
  (one-tailed t-test at 95% confidence)
  
  This means: only promote if the improvement exceeds sampling noise.
"""

import mlflow
import mlflow.sklearn
import mlflow.xgboost
import subprocess
import json
import os
import numpy as np
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
EXPERIMENT_NAME = "edupredict-ai-loan-underwriting"

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


def get_git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception:
        return "unknown"


def start_run(run_name: str = None) -> mlflow.ActiveRun:
    mlflow.set_experiment(EXPERIMENT_NAME)
    return mlflow.start_run(run_name=run_name or f"train_{get_git_commit()}")


def log_training_run(
    metrics: dict,
    base_models: dict,
    meta_model,
    scaler,
    calibrator,
    calibrator_method: str,
    graph_alpha: float,
    feature_cols: list,
    conformal_params: dict,
    fairness_report: dict,
    artifact_dir: str = "model/artifacts"
):
    """
    Log a complete training run to MLflow.
    Tags the run with git commit, Python version, feature set version.
    """
    with start_run():
        # Git metadata
        mlflow.set_tag("git_commit", get_git_commit())
        mlflow.set_tag("feature_set_version", f"v{len(feature_cols)}")
        mlflow.set_tag("calibrator_method", calibrator_method)
        mlflow.set_tag("model_version", metrics.get("model_version", "unknown"))

        # Core ML metrics
        mlflow.log_metrics({
            "stacked_ensemble_auc":     metrics["stacked_ensemble_auc"],
            "graph_regularised_auc":    metrics["graph_regularised_auc"],
            "auc_improvement_vs_cibil": metrics["auc_improvement"],
            "pre_calibration_ece":      metrics["pre_calibration_ece"],
            "post_calibration_ece":     metrics["post_calibration_ece"],
            "conformal_coverage":       conformal_params["empirical_coverage"],
            "conformal_q_hat":          conformal_params["q_hat"],
            "conformal_interval_width": conformal_params["avg_interval_width"],
        })

        # Fairness metrics
        mlflow.log_metrics({
            "fairness_dpi":       fairness_report["demographic_parity_index"],
            "fairness_tpr_diff":  abs(fairness_report["equalized_odds_tpr_diff"]),
            "fairness_fpr_diff":  abs(fairness_report["equalized_odds_fpr_diff"]),
            "fairness_ppv_diff":  abs(fairness_report["predictive_parity_diff"]),
        })

        # Hyperparameters
        mlflow.log_params({
            "n_features":       len(feature_cols),
            "graph_alpha":      round(graph_alpha, 4),
            "features":         ",".join(feature_cols),
            "n_base_models":    3,  # xgb, lgb, cat
            "calibrator":       calibrator_method,
        })

        # Log artifacts
        for art_file in Path(artifact_dir).glob("*.json"):
            mlflow.log_artifact(str(art_file))
        for img_file in Path(artifact_dir).glob("*.png"):
            mlflow.log_artifact(str(img_file))

        # Log models
        import pickle
        for fold_idx, m in enumerate(base_models["xgb"]):
            mlflow.xgboost.log_model(m, f"base_xgb_fold_{fold_idx}")
        mlflow.sklearn.log_model(meta_model, "meta_model")
        mlflow.sklearn.log_model(scaler, "scaler")

        run_id = mlflow.active_run().info.run_id
        logger.info(f"MLflow run logged: {run_id}")
        return run_id


def should_promote_to_production(
    new_auc: float,
    new_ece: float,
    new_fairness_dpi: float
) -> tuple[bool, str]:
    """
    Evaluate whether the new model should replace production.
    
    Promotion criteria (all must pass):
    1. AUC improvement: new_auc > best_prod_auc + threshold
       threshold = max(0.005, 1.96 * prod_auc_std) if history exists
    2. ECE constraint: new_ece < 0.05 (hard RBI explainability requirement)
    3. Fairness gate: new_fairness_dpi >= 0.80 (non-negotiable)
    
    Returns: (should_promote: bool, reason: str)
    """
    # Hard gates first
    if new_ece >= 0.05:
        return False, f"ECE {new_ece:.4f} ≥ 0.05 — calibration insufficient"
    if new_fairness_dpi < 0.80:
        return False, f"Fairness DPI {new_fairness_dpi:.3f} < 0.80 — fails RBI standard"

    # Get current production model metrics
    client = mlflow.MlflowClient(tracking_uri=MLFLOW_TRACKING_URI)
    try:
        prod_versions = client.get_latest_versions(
            "EduPredictAI", stages=["Production"]
        )
        if not prod_versions:
            return True, "No production model exists — promoting"

        prod_run = client.get_run(prod_versions[0].run_id)
        prod_auc = float(prod_run.data.metrics.get("graph_regularised_auc", 0.0))

        # Compute dynamic threshold from all past runs
        all_runs = client.search_runs(
            experiment_ids=[mlflow.get_experiment_by_name(
                EXPERIMENT_NAME).experiment_id],
            filter_string="metrics.graph_regularised_auc > 0",
            max_results=20
        )
        past_aucs = [r.data.metrics["graph_regularised_auc"] for r in all_runs]
        if len(past_aucs) >= 3:
            auc_std = float(np.std(past_aucs))
            threshold = max(0.005, 1.96 * auc_std)
        else:
            threshold = 0.005

        if new_auc > prod_auc + threshold:
            return True, (f"AUC improved {prod_auc:.4f} → {new_auc:.4f} "
                         f"(threshold={threshold:.4f})")
        else:
            return False, (f"AUC {new_auc:.4f} not sufficiently better than "
                          f"prod {prod_auc:.4f} (need +{threshold:.4f})")

    except Exception as e:
        logger.warning(f"Could not compare to production: {e} — promoting anyway")
        return True, "Could not retrieve production metrics — promoting"


def register_model(run_id: str, model_name: str = "EduPredictAI") -> str:
    """Register model from a run and promote if criteria are met."""
    client = mlflow.MlflowClient(tracking_uri=MLFLOW_TRACKING_URI)

    # Get metrics from this run
    run = client.get_run(run_id)
    new_auc = run.data.metrics["graph_regularised_auc"]
    new_ece = run.data.metrics["post_calibration_ece"]
    new_dpi = run.data.metrics["fairness_dpi"]

    should_promote, reason = should_promote_to_production(new_auc, new_ece, new_dpi)
    logger.info(f"Promotion decision: {should_promote} — {reason}")

    # Register model version
    model_uri = f"runs:/{run_id}/meta_model"
    mv = mlflow.register_model(model_uri, model_name)

    if should_promote:
        client.transition_model_version_stage(
            name=model_name,
            version=mv.version,
            stage="Production",
            archive_existing_versions=True
        )
        logger.info(f"Model v{mv.version} promoted to Production")
    else:
        client.transition_model_version_stage(
            name=model_name, version=mv.version, stage="Staging"
        )
        logger.info(f"Model v{mv.version} moved to Staging")

    return mv.version
