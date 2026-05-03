"""
Auto-generate model card from training artifacts.
Model cards (Mitchell et al., 2019) are required by:
  - RBI FREE-AI Framework (August 2025): AI governance disclosure
  - Google AI responsible practices
  - Any NBFC compliance audit
  
This script reads all JSON artifacts and generates a complete
model card as both markdown and JSON.
"""

import json
import time
import os
from pathlib import Path
from datetime import datetime


def generate_model_card() -> dict:
    base = Path("model/artifacts")
    
    # Check if artifacts exist
    if not (base / "metrics.json").exists():
        print("Warning: metrics.json not found. Run training first.")
        return {}

    metrics = json.loads((base / "metrics.json").read_text())
    fairness = json.loads((base / "fairness_report.json").read_text())
    conformal = json.loads((base / "conformal_params.json").read_text())
    feature_ranges = json.loads((base / "feature_ranges.json").read_text())
    cal_params = json.loads((base / "calibration_params.json").read_text())
    graph_params = json.loads((base / "graph_params.json").read_text())
    
    group_thresholds = {}
    if (base / "group_thresholds.json").exists():
        group_thresholds = json.loads((base / "group_thresholds.json").read_text())

    card = {
        "model_details": {
            "name": "EduPredict AI Student Loan Underwriting Model",
            "version": metrics["model_version"],
            "type": "Stacked ensemble (XGBoost + LightGBM + CatBoost) + Logistic meta-learner",
            "task": "Binary classification — student loan repayment prediction",
            "date_trained": datetime.utcnow().isoformat(),
            "license": "MIT",
            "contact": "dpo@edupredict.ai",
        },
        "intended_use": {
            "primary_use": "Advisory risk scoring for Indian student education loan applications",
            "primary_users": "NBFC loan officers, DSA partners",
            "out_of_scope": [
                "Sole basis for credit denial without human review",
                "Non-education loans",
                "Students outside India",
                "Any use without explicit DPDP Act consent",
            ],
        },
        "training_data": {
            "sources": [
                "IEEE DataPort: Engineering Graduate Employability (12k Indian students)",
                "NIRF 2024: Ministry of Education Institutional Rankings",
                "Kaggle: Indian Student Placement Dataset 2025",
                "Live: Naukri & LinkedIn job APIs (demand consensus)",
                "Live: data.gov.in PLFS (macro indicators)",
            ],
            "known_limitations": [
                "Repayment labels are synthetic (calibrated to RBI 4.4% NPA)",
                "Field-level salary medians used as proxy for individual income",
                "No real Indian student loan repayment microdata available in training set",
            ],
            "n_training_samples": metrics.get("train_size", "see metrics.json"),
        },
        "performance": {
            "primary_metric": "ROC-AUC (graph-regularised)",
            "auc": metrics["graph_regularised_auc"],
            "baseline_auc_cibil_only": metrics["baseline_cibil_auc"],
            "auc_improvement": metrics["auc_improvement"],
            "calibration_ece": metrics["post_calibration_ece"],
            "calibration_method": cal_params.get("method", "isotonic"),
            "conformal_coverage_90pct": conformal["empirical_coverage"],
            "conformal_q_hat": conformal["q_hat"],
        },
        "fairness": {
            "sensitive_attribute": "Field of study (proxy for socioeconomic background)",
            "metrics": {
                "demographic_parity_index": fairness["demographic_parity_index"],
                "equalized_odds_tpr_diff": fairness["equalized_odds_tpr_diff"],
                "equalized_odds_fpr_diff": fairness["equalized_odds_fpr_diff"],
                "predictive_parity_diff": fairness["predictive_parity_diff"],
            },
            "overall_fair": fairness["overall_fair"],
            "fairness_standard": "80% rule (ECOA / RBI FREE-AI Framework)",
            "note": (
                "Chouldechova (2017) impossibility theorem: equalized odds and "
                "predictive parity cannot both hold when base rates differ. "
                "We report both and let the operator choose based on policy."
            ),
        },
        "fairness_calibration": {
            "threshold_disadvantaged": group_thresholds.get("threshold_disadvantaged"),
            "threshold_advantaged": group_thresholds.get("threshold_advantaged"),
            "validation_fpr_diff": group_thresholds.get("validation_fpr_diff"),
            "validation_tpr_diff": group_thresholds.get("validation_tpr_diff"),
            "computed_at": group_thresholds.get("computed_at")
        },
        "architecture": {
            "base_learners": ["XGBoost (Dart)", "LightGBM (Dart)", "CatBoost (Ordered)"],
            "meta_learner": "Logistic Regression on OOF predictions",
            "calibration": cal_params.get("method", "isotonic"),
            "graph_regularisation": {
                "method": "RBF kernel k-NN (k=50)",
                "alpha": graph_params["alpha"],
                "sigma": "Median heuristic",
            },
            "uncertainty": "Split conformal prediction (Angelopoulos & Bates 2021)",
        },
        "features": {
            col: {"range": ranges, "description": _feature_description(col)}
            for col, ranges in feature_ranges.items()
        },
        "regulatory_compliance": {
            "rbi_free_ai": "August 2025 — Explainability via SHAP, Fairness via DPI",
            "dpdp_act_2023": "Consent capture implemented, data retention policies defined",
            "adverse_action": "Reason codes AA-01 through AA-09 generated for RED tier",
        },
    }

    # Write markdown version
    md = _card_to_markdown(card)
    Path("MODEL_CARD.md").write_text(md)
    (base / "model_card.json").write_text(json.dumps(card, indent=2))

    print("Model card generated: MODEL_CARD.md and model/artifacts/model_card.json")
    return card


def _feature_description(col: str) -> str:
    desc = {
        "cgpa_normalized":          "CGPA normalised to [0,1] by dividing by 10",
        "internships_count":        "Number of internships completed",
        "backlogs":                 "Number of academic backlogs/arrears",
        "median_salary_normalized": "Median salary for field, normalised to [0,1]",
        "potential_score":          "Weighted composite: 0.35*CGPA + 0.25*internships + 0.25*placement + 0.15*salary",
        "demand_proxy":             "Normalised job posting count for student's field",
        "placement_rate_for_field": "Institution placement rate [0,1]",
        "demand_velocity_per_day":  "OLS slope of job count over time (jobs/day)",
        "demand_acceleration":      "Second derivative of job demand (jobs/day²)",
        "velocity_r_squared":       "OLS fit quality for demand trend (0=noisy, 1=clean)",
        "demand_momentum":          "EWMA: 0.3*velocity + 0.7*demand_proxy",
        "market_hhi":               "Herfindahl-Hirschman Index of field concentration",
        "macro_index":              "India Macro Repayment Index: composite of unemployment, repo rate, CPI, hiring",
        "backlogs_missing":         "Binary indicator: 1 if backlog data was imputed using field median",
    }
    return desc.get(col, col)


def _card_to_markdown(card: dict) -> str:
    p = card["performance"]
    f = card["fairness"]["metrics"]
    return f"""# EduPredict AI — Model Card

## Model Details
- **Version**: {card['model_details']['version']}
- **Task**: {card['model_details']['task']}
- **Date**: {card['model_details']['date_trained'][:10]}
- **License**: {card['model_details']['license']}

## Intended Use
{card['intended_use']['primary_use']}

**Not intended for**: {', '.join(card['intended_use']['out_of_scope'])}

## Performance

| Metric | Value |
|--------|-------|
| Graph-regularised AUC | {p['auc']:.4f} |
| vs CIBIL-only baseline | +{p['auc_improvement']:.4f} |
| Calibration ECE | {p['calibration_ece']:.4f} |
| Conformal coverage (90% target) | {p['conformal_coverage_90pct']:.3f} |

## Fairness Audit

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Demographic Parity Index | {f['demographic_parity_index']:.4f} | ≥ 0.80 | {'PASS' if f['demographic_parity_index'] >= 0.80 else 'FAIL'} |
| Equalized Odds TPR diff | {abs(f['equalized_odds_tpr_diff']):.4f} | ≤ 0.10 | {'PASS' if abs(f['equalized_odds_tpr_diff']) <= 0.10 else 'FAIL'} |
| Equalized Odds FPR diff | {abs(f['equalized_odds_fpr_diff']):.4f} | ≤ 0.10 | {'PASS' if abs(f['equalized_odds_fpr_diff']) <= 0.10 else 'FAIL'} |
| Predictive Parity diff | {abs(f['predictive_parity_diff']):.4f} | ≤ 0.10 | {'PASS' if abs(f['predictive_parity_diff']) <= 0.10 else 'FAIL'} |

## Regulatory Compliance
- **RBI FREE-AI Framework (August 2025)**: Explainability via SHAP, Fairness via DPI ≥ 0.80
- **DPDP Act 2023**: Per-source consent capture, 72h deletion on withdrawal
- **Adverse Action**: Reason codes generated for all RED-tier decisions

## Fairness Calibration (Post-processing)
| Group | Threshold |
|-------|-----------|
| Disadvantaged | {card['fairness_calibration']['threshold_disadvantaged']} |
| Advantaged | {card['fairness_calibration']['threshold_advantaged']} |

*Validation after calibration: FPR diff = {card['fairness_calibration']['validation_fpr_diff']:.4f}, TPR diff = {card['fairness_calibration']['validation_tpr_diff']:.4f}*

## Known Limitations
- Repayment labels are synthetic (calibrated to RBI 4.4% NPA)
- Velocity features require ≥2 DAG snapshots (zeros until second run)
- Field-level salary medians used as proxy for individual income
"""


if __name__ == "__main__":
    generate_model_card()
