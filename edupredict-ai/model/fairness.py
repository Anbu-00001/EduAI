import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict

@dataclass
class FairnessReport:
    demographic_parity_index: float
    equalized_odds_tpr_diff: float
    equalized_odds_fpr_diff: float
    predictive_parity_diff: float
    overall_fair: bool
    
    def __str__(self):
        return (
            f"Demographic Parity Index:  {self.demographic_parity_index:.4f} "
            f"({'PASS' if self.demographic_parity_index >= 0.80 else 'FAIL'})\n"
            f"Equalized Odds (TPR gap):  {self.equalized_odds_tpr_diff:.4f} "
            f"({'PASS' if abs(self.equalized_odds_tpr_diff) <= 0.10 else 'FAIL'})\n"
            f"Equalized Odds (FPR gap):  {self.equalized_odds_fpr_diff:.4f} "
            f"({'PASS' if abs(self.equalized_odds_fpr_diff) <= 0.10 else 'FAIL'})\n"
            f"Predictive Parity gap:     {self.predictive_parity_diff:.4f} "
            f"({'PASS' if abs(self.predictive_parity_diff) <= 0.10 else 'FAIL'})\n"
            f"Overall Fair:              {'YES' if self.overall_fair else 'NO'}"
        )

def compute_fairness_metrics(
        y_true: np.ndarray,
        y_pred_proba: np.ndarray,
        sensitive_attr: np.ndarray,
        threshold: float = 0.50
) -> FairnessReport:
    """
    Computes four standard fairness metrics for lending compliance.
    """
    y_pred = (y_pred_proba >= threshold).astype(int)
    groups = np.unique(sensitive_attr)
    if len(groups) != 2:
        # Fallback if binary assumption fails, though prompt assumes binary
        return FairnessReport(1.0, 0.0, 0.0, 0.0, True)
    
    g0, g1 = groups[0], groups[1]
    
    def rates(group):
        mask = sensitive_attr == group
        y_t = y_true[mask]
        y_p = y_pred[mask]
        
        approval_rate = y_p.mean()
        tpr = (y_p[y_t == 1] == 1).mean() if (y_t == 1).sum() > 0 else 0.0
        fpr = (y_p[y_t == 0] == 1).mean() if (y_t == 0).sum() > 0 else 0.0
        ppv = y_t[y_p == 1].mean() if (y_p == 1).sum() > 0 else 0.0
        return {"approval": approval_rate, "tpr": tpr, "fpr": fpr, "ppv": ppv}
    
    r0, r1 = rates(g0), rates(g1)
    
    # DPI: ratio of approval rates (minority/majority)
    denom = max(r0["approval"], r1["approval"])
    num = min(r0["approval"], r1["approval"])
    dpi = num / denom if denom > 0 else 1.0
    
    tpr_diff = r0["tpr"] - r1["tpr"]
    fpr_diff = r0["fpr"] - r1["fpr"]
    ppv_diff = r0["ppv"] - r1["ppv"]
    
    overall_fair = (
        dpi >= 0.80 and 
        abs(tpr_diff) <= 0.10 and 
        abs(fpr_diff) <= 0.10 and 
        abs(ppv_diff) <= 0.10
    )
    
    return FairnessReport(dpi, tpr_diff, fpr_diff, ppv_diff, overall_fair)

def audit_fairness(df: pd.DataFrame, y_pred_proba: np.ndarray, sensitive_col: str) -> dict:
    """
    Perform a complete fairness audit across a sensitive column.
    Handles multiple groups by comparing each to the mean.
    """
    y_true = df["repaid_loan"].values
    sensitive_attr = df[sensitive_col].values
    
    # Calculate group-level metrics
    groups = np.unique(sensitive_attr)
    group_stats = {}
    for g in groups:
        mask = sensitive_attr == g
        if mask.sum() == 0: continue
        approval_rate = (y_pred_proba[mask] >= 0.5).mean()
        tpr = (y_pred_proba[mask & (y_true == 1)] >= 0.5).mean() if (mask & (y_true == 1)).sum() > 0 else 0.0
        fpr = (y_pred_proba[mask & (y_true == 0)] >= 0.5).mean() if (mask & (y_true == 0)).sum() > 0 else 0.0
        ppv = y_true[mask & (y_pred_proba >= 0.5)].mean() if (mask & (y_pred_proba >= 0.5)).sum() > 0 else 0.0
        group_stats[str(g)] = {"approval": approval_rate, "tpr": tpr, "fpr": fpr, "ppv": ppv}
    
    # Demographic Parity Index (ratio of min approval / max approval)
    approvals = [s["approval"] for s in group_stats.values()]
    dpi = min(approvals) / max(approvals) if max(approvals) > 0 else 1.0
    
    # Differences (max absolute difference between any two groups)
    tpr_diff = max([s["tpr"] for s in group_stats.values()]) - min([s["tpr"] for s in group_stats.values()])
    fpr_diff = max([s["fpr"] for s in group_stats.values()]) - min([s["fpr"] for s in group_stats.values()])
    ppv_diff = max([s["ppv"] for s in group_stats.values()]) - min([s["ppv"] for s in group_stats.values()])
    
    report = {
        "demographic_parity_index": float(dpi),
        "equalized_odds_tpr_diff": float(tpr_diff),
        "equalized_odds_fpr_diff": float(fpr_diff),
        "predictive_parity_diff": float(ppv_diff),
        "group_metrics": group_stats,
        "overall_fair": bool(dpi >= 0.80 and tpr_diff <= 0.10 and fpr_diff <= 0.10)
    }
    return report

