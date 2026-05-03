import numpy as np
import json
import logging
from pathlib import Path
from datetime import datetime, timezone
from sklearn.metrics import confusion_matrix

logger = logging.getLogger(__name__)

def compute_group_thresholds(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    sensitive_attr: np.ndarray,
    tpr_tolerance: float = 0.10,
    fpr_tolerance: float = 0.10,
) -> dict[str, float]:
    """
    Find per-group thresholds (one for disadvantaged=1, one for advantaged=0)
    such that:
      |TPR_group0 - TPR_group1| <= tpr_tolerance
      |FPR_group0 - FPR_group1| <= fpr_tolerance

    Method: grid search over threshold pairs (t0, t1) in np.arange(0.1, 0.9, 0.01)
    Objective: minimise FPR diff subject to TPR diff constraint.
    Secondary objective: maximise (TPR_0 + TPR_1) / 2 (keep approval rates high).
    """
    thresholds = np.arange(0.1, 0.9, 0.01)
    best_t0, best_t1 = 0.5, 0.5
    min_fpr_diff = float('inf')
    max_avg_tpr = -1.0
    best_tpr_diff = 1.0
    
    # Split data by group
    mask1 = (sensitive_attr == 1)
    mask0 = (sensitive_attr == 0)
    
    y_true1, y_prob1 = y_true[mask1], y_prob[mask1]
    y_true0, y_prob0 = y_true[mask0], y_prob[mask0]

    found = False
    for t0 in thresholds:
        # Precompute metrics for group 0
        y_pred0 = (y_prob0 >= t0).astype(int)
        tn0, fp0, fn0, tp0 = confusion_matrix(y_true0, y_pred0, labels=[0, 1]).ravel()
        tpr0 = tp0 / (tp0 + fn0) if (tp0 + fn0) > 0 else 0
        fpr0 = fp0 / (fp0 + tn0) if (fp0 + tn0) > 0 else 0
        
        for t1 in thresholds:
            # Precompute metrics for group 1
            y_pred1 = (y_prob1 >= t1).astype(int)
            tn1, fp1, fn1, tp1 = confusion_matrix(y_true1, y_pred1, labels=[0, 1]).ravel()
            tpr1 = tp1 / (tp1 + fn1) if (tp1 + fn1) > 0 else 0
            fpr1 = fp1 / (fp1 + tn1) if (fp1 + tn1) > 0 else 0
            
            tpr_diff = abs(tpr0 - tpr1)
            fpr_diff = abs(fpr0 - fpr1)
            
            if tpr_diff <= tpr_tolerance and fpr_diff <= fpr_tolerance:
                found = True
                avg_tpr = (tpr0 + tpr1) / 2
                
                # Primary: minimize FPR diff, Secondary: maximize avg TPR
                if fpr_diff < min_fpr_diff or (fpr_diff == min_fpr_diff and avg_tpr > max_avg_tpr):
                    min_fpr_diff = fpr_diff
                    max_avg_tpr = avg_tpr
                    best_tpr_diff = tpr_diff
                    best_t0, best_t1 = t0, t1

    if not found:
        raise ValueError(f"No threshold pair satisfies TPR tolerance {tpr_tolerance} and FPR tolerance {fpr_tolerance}")

    return {
        "threshold_disadvantaged": float(best_t1),
        "threshold_advantaged": float(best_t0),
        "validation_fpr_diff": float(min_fpr_diff),
        "validation_tpr_diff": float(best_tpr_diff)
    }

def apply_group_thresholds(
    y_prob: np.ndarray,
    sensitive_attr: np.ndarray,
    thresholds: dict[str, float],
) -> np.ndarray:
    """
    Apply group-specific thresholds to produce binary predictions.
    disadvantaged (sensitive_attr=1) uses threshold_disadvantaged.
    advantaged   (sensitive_attr=0) uses threshold_advantaged.
    """
    y_pred = np.zeros_like(y_prob)
    t1 = thresholds["threshold_disadvantaged"]
    t0 = thresholds["threshold_advantaged"]
    
    y_pred[sensitive_attr == 1] = (y_prob[sensitive_attr == 1] >= t1).astype(int)
    y_pred[sensitive_attr == 0] = (y_prob[sensitive_attr == 0] >= t0).astype(int)
    
    return y_pred

def save_group_thresholds(thresholds: dict, artifact_dir: Path) -> None:
    """
    Save to model/artifacts/group_thresholds.json.
    """
    output_path = artifact_dir / "group_thresholds.json"
    data = {
        "computed_at": datetime.now(timezone.utc).isoformat(),
        **thresholds
    }
    output_path.write_text(json.dumps(data, indent=2))
    logger.info(f"Saved group thresholds to {output_path}")

def load_group_thresholds(artifact_dir: Path) -> dict:
    """
    Load group_thresholds.json.
    """
    path = artifact_dir / "group_thresholds.json"
    if not path.exists():
        raise FileNotFoundError(f"Fairness calibration file not found at {path}")
    return json.loads(path.read_text())
