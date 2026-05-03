# EduPredict AI — Known Data Gaps & Disclosure
**Date**: April 2026
**Compliance Status**: RBI FREE-AI Framework (August 2025) compliant.

This document formally acknowledges the data limitations in the current EduPredict AI (v5.0) model, as required by the Responsible AI guidelines for NBFCs.

## Gap 1: Synthetic Repayment Labels
- **Limitation**: No open-source micro-level Indian student loan repayment dataset exists.
- **Mitigation**: Repayment labels (`repaid_loan`) are synthetic, derived from a domain-calibrated formula.
- **Grounding**: The formula is calibrated to the **RBI Annual Report 2024** education loan gross NPA rate of **4.4%**.
- **Impact**: The model predicts *likelihood of repayment* under these calibrated conditions, not absolute creditworthiness.

## Gap 2: US Consumer Loan Proxy
- **Limitation**: Legacy training artifacts included features derived from Lending Club (US) data.
- **Mitigation**: Phase 5 upgrade has removed all Lending Club dependencies.
- **Current Source**: Model now trains on **IEEE DataPort** (Engineering Graduate Employability) and **NIRF 2024** medians.

## Gap 3: NIRF Salary Aggregation
- **Limitation**: NIRF provides institution-level median salaries, not individual student salaries.
- **Mitigation**: Model uses field-level median salary normalisation derived from NIRF 2024 Engineering reports.
- **Impact**: Individual variance in salary within a college/field is not fully captured.

## Gap 4: Temporal Cold Start
- **Limitation**: Demand velocity features (`demand_velocity_per_day`) require at least 2 DAG snapshots.
- **Status**: Zeros are used for first-run students. Accuracy improves after 7 days of system uptime.

## Gap 5: Data.gov.in PLFS Staleness
- **Limitation**: PLFS APIs for specific resource IDs frequently change or go offline.
- **Mitigation**: System implements an automatic fallback to `IMRI_DEFAULT` (0.72) when APIs fail, ensuring continuity.
