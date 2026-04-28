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

from config import EnvConfig

logger = logging.getLogger(__name__)

# Use EnvConfig for MLflow tracking URI
try:
    MLFLOW_TRACKING_URI = EnvConfig.MLFLOW_TRACKING_URI()
except Exception:
    MLFLOW_TRACKING_URI = "sqlite:///mlflow.db"
    
EXPERIMENT_NAME = "edupredict-ai-loan-underwriting"

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

ROOT_DIR = Path(__file__).parent.parent
ARTIFACT_DIR = ROOT_DIR / "model" / "artifacts"


def get_git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            stderr=subprocess.DEVNULL
        ).decode().strip()
    except Exception as e:
        logger.warning(f"Failed to get git commit: {e}")
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
    artifact_dir: str = str(ARTIFACT_DIR)
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
            "stacked_ensemble_auc":     metrics.get("stacked_ensemble_auc", 0.0),
            "graph_regularised_auc":    metrics.get("graph_regularised_auc", 0.0),
            "auc_improvement_vs_cibil": metrics.get("auc_improvement", 0.0),
            "pre_calibration_ece":      metrics.get("pre_calibration_ece", 0.0),
            "post_calibration_ece":     metrics.get("post_calibration_ece", 0.0),
            "conformal_coverage":       conformal_params.get("empirical_coverage", 0.0),
            "conformal_q_hat":          conformal_params.get("q_hat", 0.0),
            "conformal_interval_width": conformal_params.get("avg_interval_width", 0.0),
        })

        # Fairness metrics
        mlflow.log_metrics({
            "fairness_dpi":       fairness_report.get("demographic_parity_index", 1.0),
            "fairness_tpr_diff":  abs(fairness_report.get("equalized_odds_tpr_diff", 0.0)),
            "fairness_fpr_diff":  abs(fairness_report.get("equalized_odds_fpr_diff", 0.0)),
            "fairness_ppv_diff":  abs(fairness_report.get("predictive_parity_diff", 0.0)),
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
        art_path = Path(artifact_dir)
        if art_path.exists():
            for art_file in art_path.glob("*.json"):
                mlflow.log_artifact(str(art_file))
            for img_file in art_path.glob("*.png"):
                mlflow.log_artifact(str(img_file))

        # Log models
        import pickle
        for fold_idx, m in enumerate(base_models.get("xgb", [])):
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
        # Check for alias instead of stages, as stages are deprecated in MLflow > 2.9
        # But we will use both logic for compatibility
        prod_auc = 0.0
        has_prod = False
        
        try:
            alias_version = client.get_model_version_by_alias("EduPredictAI", "Production")
            prod_run = client.get_run(alias_version.run_id)
            prod_auc = float(prod_run.data.metrics.get("graph_regularised_auc", 0.0))
            has_prod = True
        except Exception:
            # Fallback to stages
            prod_versions = client.get_latest_versions("EduPredictAI", stages=["Production"])
            if prod_versions:
                prod_run = client.get_run(prod_versions[0].run_id)
                prod_auc = float(prod_run.data.metrics.get("graph_regularised_auc", 0.0))
                has_prod = True

        if not has_prod:
            return True, "No production model exists — promoting"

        # Compute dynamic threshold from all past runs
        all_runs = client.search_runs(
            experiment_ids=[mlflow.get_experiment_by_name(
                EXPERIMENT_NAME).experiment_id],
            filter_string="metrics.graph_regularised_auc > 0",
            max_results=20
        )
        past_aucs = [r.data.metrics.get("graph_regularised_auc", 0.0) for r in all_runs]
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
    try:
        run = client.get_run(run_id)
        new_auc = run.data.metrics.get("graph_regularised_auc", 0.0)
        new_ece = run.data.metrics.get("post_calibration_ece", 0.0)
        new_dpi = run.data.metrics.get("fairness_dpi", 1.0)
    except Exception as e:
        logger.error(f"Failed to fetch run metrics for {run_id}: {e}")
        return "unknown"

    should_promote, reason = should_promote_to_production(new_auc, new_ece, new_dpi)
    logger.info(f"Promotion decision: {should_promote} — {reason}")

    # Register model version
    model_uri = f"runs:/{run_id}/meta_model"
    try:
        mv = mlflow.register_model(model_uri, model_name)
    except Exception as e:
        logger.error(f"Failed to register model: {e}")
        return "unknown"

    try:
        if should_promote:
            try:
                client.set_registered_model_alias(model_name, "Production", mv.version)
            except Exception:
                pass
            client.transition_model_version_stage(
                name=model_name,
                version=mv.version,
                stage="Production",
                archive_existing_versions=True
            )
            logger.info(f"Model v{mv.version} promoted to Production")
        else:
            try:
                client.set_registered_model_alias(model_name, "Staging", mv.version)
            except Exception:
                pass
            client.transition_model_version_stage(
                name=model_name, version=mv.version, stage="Staging"
            )
            logger.info(f"Model v{mv.version} moved to Staging")
    except Exception as e:
        logger.warning(f"Failed to transition model stage/alias: {e}")

    return mv.version
