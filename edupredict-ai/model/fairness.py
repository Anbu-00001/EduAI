import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)

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

def is_disadvantaged(cgpa_norm: float, annual_income: Optional[float] = None, institution_verified: bool = True) -> int:
    """
    Compute the protected attribute (disadvantaged flag).
    Uses cgpa, annual family income, and institution verification status.
    Returns 1 (disadvantaged) or 0 (advantaged).
    """
    from config import EnvConfig
    median_threshold = EnvConfig.CGPA_DISADVANTAGED_THRESHOLD()
    
    below_median = cgpa_norm < median_threshold
    low_income = annual_income is not None and annual_income < 300_000
    unverified = not institution_verified
    
    return int(below_median and (low_income or unverified))

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
        raise ValueError(f"sensitive_attr must have exactly 2 unique groups. Found {len(groups)}")
    
    g0, g1 = groups[0], groups[1]
    
    def rates(group):
        mask = sensitive_attr == group
        y_t = y_true[mask]
        y_p = y_pred[mask]
        
        approval_rate = y_p.mean()
        
        pos_count = (y_t == 1).sum()
        if pos_count == 0:
            logger.warning(f"Group {group} has NO positive examples in the set. TPR set to 0.0.")
            tpr = 0.0
        else:
            tpr = (y_p[y_t == 1] == 1).mean()
            
        neg_count = (y_t == 0).sum()
        if neg_count == 0:
            logger.warning(f"Group {group} has NO negative examples in the set. FPR set to 0.0.")
            fpr = 0.0
        else:
            fpr = (y_p[y_t == 0] == 1).mean()
            
        pred_pos_count = (y_p == 1).sum()
        ppv = y_t[y_p == 1].mean() if pred_pos_count > 0 else 0.0
        
        return {"approval": approval_rate, "tpr": tpr, "fpr": fpr, "ppv": ppv}
    
    r0, r1 = rates(g0), rates(g1)
    
    # DPI: ratio of min approval rate to max approval rate
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
    
    groups = np.unique(sensitive_attr)
    group_stats = {}
    for g in groups:
        mask = sensitive_attr == g
        if mask.sum() == 0: continue
        approval_rate = (y_pred_proba[mask] >= 0.5).mean()
        
        pos_count = (mask & (y_true == 1)).sum()
        if pos_count == 0:
            logger.warning(f"Group {g} has NO positive examples in the set. TPR set to 0.0.")
            tpr = 0.0
        else:
            tpr = (y_pred_proba[mask & (y_true == 1)] >= 0.5).mean()
            
        neg_count = (mask & (y_true == 0)).sum()
        if neg_count == 0:
            logger.warning(f"Group {g} has NO negative examples in the set. FPR set to 0.0.")
            fpr = 0.0
        else:
            fpr = (y_pred_proba[mask & (y_true == 0)] >= 0.5).mean()
            
        pred_pos_count = (mask & (y_pred_proba >= 0.5)).sum()
        ppv = y_true[mask & (y_pred_proba >= 0.5)].mean() if pred_pos_count > 0 else 0.0
        group_stats[str(g)] = {"approval": float(approval_rate), "tpr": float(tpr), "fpr": float(fpr), "ppv": float(ppv)}
    
    approvals = [s["approval"] for s in group_stats.values()]
    dpi = min(approvals) / max(approvals) if max(approvals) > 0 else 1.0
    
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

def apply_fairness_constraint(
        y_pred_proba: np.ndarray,
        sensitive_attr: np.ndarray,
        target_dpi: float = 0.80,
        global_threshold: float = 0.50
) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Adjusts thresholds per group to satisfy Demographic Parity Index (DPI).
    Finds the majority group's approval rate at the global_threshold, 
    then lowers the threshold for the minority group to achieve the target DPI.
    
    Returns:
        adjusted_preds: binary predictions {0,1}
        group_thresholds: dictionary of chosen thresholds per group
    """
    groups = np.unique(sensitive_attr)
    if len(groups) != 2:
        raise ValueError("apply_fairness_constraint requires exactly 2 groups")
        
    g0, g1 = groups[0], groups[1]
    
    # Calculate initial approval rates at global threshold
    p0 = (y_pred_proba[sensitive_attr == g0] >= global_threshold).mean()
    p1 = (y_pred_proba[sensitive_attr == g1] >= global_threshold).mean()
    
    majority_group = g0 if p0 > p1 else g1
    minority_group = g1 if majority_group == g0 else g0
    
    majority_approval = max(p0, p1)
    
    # Target approval for minority group to hit DPI target
    target_approval_minority = majority_approval * target_dpi
    
    # Clip to valid quantile range [0.0, 1.0]
    target_approval_minority = np.clip(target_approval_minority, 0.0, 1.0)
    
    # Find new threshold for minority group
    probs_minority = y_pred_proba[sensitive_attr == minority_group]
    
    if len(probs_minority) == 0:
        minority_thresh = global_threshold
    else:
        # Quantile expects value between 0 and 1. 
        # If target approval is T, we want top T fraction to be 1, so threshold is at quantile (1 - T).
        quantile_level = np.clip(1.0 - target_approval_minority, 0.0, 1.0)
        minority_thresh = float(np.quantile(probs_minority, quantile_level))
    
    # Apply thresholds
    group_thresholds = {str(majority_group): global_threshold, str(minority_group): minority_thresh}
    
    adjusted_preds = np.zeros_like(y_pred_proba, dtype=int)
    
    for g in groups:
        mask = sensitive_attr == g
        thresh = group_thresholds[str(g)]
        adjusted_preds[mask] = (y_pred_proba[mask] >= thresh).astype(int)
        
    return adjusted_preds, group_thresholds
