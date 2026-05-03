# EduPredict AI — Model Card

## Model Details
- **Version**: v4.0-production
- **Task**: Binary classification — student loan repayment prediction
- **Date**: 2026-04-28
- **License**: MIT

## Intended Use
Advisory risk scoring for Indian student education loan applications

**Not intended for**: Sole basis for credit denial without human review, Non-education loans, Students outside India, Any use without explicit DPDP Act consent

## Performance

| Metric | Value |
|--------|-------|
| Graph-regularised AUC | 0.8265 |
| vs CIBIL-only baseline | +0.2065 |
| Calibration ECE | 0.0098 |
| Conformal coverage (90% target) | 0.882 |

## Fairness Audit

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Demographic Parity Index | 0.9545 | ≥ 0.80 | PASS |
| Equalized Odds TPR diff | 0.0380 | ≤ 0.10 | PASS |
| Equalized Odds FPR diff | 0.1111 | ≤ 0.10 | FAIL |
| Predictive Parity diff | 0.1459 | ≤ 0.10 | FAIL |

## Regulatory Compliance
- **RBI FREE-AI Framework (August 2025)**: Explainability via SHAP, Fairness via DPI ≥ 0.80
- **DPDP Act 2023**: Per-source consent capture, 72h deletion on withdrawal
- **Adverse Action**: Reason codes generated for all RED-tier decisions

## Known Limitations
- Repayment labels are synthetic (calibrated to RBI 4.4% NPA)
- Velocity features require ≥2 DAG snapshots (zeros until second run)
- Field-level salary medians used as proxy for individual income
