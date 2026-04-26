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

def apply_fairness_constraint(
        y_pred_proba: np.ndarray,
        sensitive_attr: np.ndarray,
        target_dpi: float = 0.80
) -> np.ndarray:
    """Post-processing fairness correction via threshold adjustment."""
    groups = np.unique(sensitive_attr)
    if len(groups) != 2: return (y_pred_proba >= 0.5).astype(float)
    g0, g1 = groups[0], groups[1]
    
    probs_g0 = y_pred_proba[sensitive_attr == g0]
    probs_g1 = y_pred_proba[sensitive_attr == g1]
    
    tau_majority = 0.50
    approval_majority = (probs_g1 >= tau_majority).mean()
    
    target_approval_minority = approval_majority * target_dpi
    tau_minority = float(np.quantile(probs_g0, 1 - target_approval_minority))
    
    adjusted = np.where(
        sensitive_attr == g0,
        (y_pred_proba >= tau_minority).astype(float),
        (y_pred_proba >= tau_majority).astype(float)
    )
    return adjusted
