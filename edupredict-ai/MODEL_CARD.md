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
| Graph-regularised AUC | 0.7867 |
| vs CIBIL-only baseline | +0.1667 |
| Calibration ECE | 0.0258 |
| Conformal coverage (90% target) | 0.923 |

## Fairness Audit

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Demographic Parity Index | 0.8241 | ≥ 0.80 | PASS |
| Equalized Odds TPR diff | 0.0943 | ≤ 0.10 | PASS |
| Equalized Odds FPR diff | 0.1798 | ≤ 0.10 | FAIL |
| Predictive Parity diff | 0.1014 | ≤ 0.10 | FAIL |

## Regulatory Compliance
- **RBI FREE-AI Framework (August 2025)**: Explainability via SHAP, Fairness via DPI ≥ 0.80
- **DPDP Act 2023**: Per-source consent capture, 72h deletion on withdrawal
- **Adverse Action**: Reason codes generated for all RED-tier decisions

## Known Limitations
- Training data uses US consumer loan outcomes as proxy for Indian student loans
- Velocity features require ≥2 DAG snapshots (zeros until second run)
- No real Indian student repayment outcome data in training set
