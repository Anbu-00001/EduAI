"""
Calibration module — EduPredict AI

Platt Scaling:
  p_cal = sigmoid(A*s + B) where A,B minimise cross-entropy
  Limitation: assumes model scores are monotone logistic

Isotonic Regression (preferred for tree ensembles):
  Fits a non-decreasing step function f such that
  f(s_i) ≈ P(Y=1 | score = s_i)
  Guaranteed: f is non-decreasing (monotone isotonic constraint)
  Solved by Pool Adjacent Violators (PAV) algorithm in O(n log n)
  
  Better calibration for XGBoost/LGB because tree outputs are
  already piecewise constant — isotonic respects that structure.
  Platt assumes smooth logistic which is wrong for tree outputs.

ECE (Expected Calibration Error):
  ECE = Σ_b (|B_b|/n) * |acc(B_b) - conf(B_b)|
  where B_b = set of predictions in bin b
  
  Target: ECE < 0.03 (Platt typically achieves 0.05–0.08 for trees)
  Isotonic typically achieves 0.01–0.03 for tree ensembles.
"""

import numpy as np
from sklearn.isotonic import IsotonicRegression
from sklearn.calibration import calibration_curve
from scipy.optimize import minimize
import matplotlib.pyplot as plt
import logging

logger = logging.getLogger(__name__)


def isotonic_calibrate(
    raw_probs_cal: np.ndarray,
    y_cal: np.ndarray,
    raw_probs_test: np.ndarray
) -> tuple[np.ndarray, object]:
    """
    Fit isotonic regression calibrator on calibration set.
    Apply to test set.
    
    PAV algorithm ensures: if s_i < s_j then f(s_i) ≤ f(s_j)
    This is the correct inductive bias for probability calibration.
    
    out_of_bounds="clip" is used because labels are binary {0,1},
    so clipping to [min_y, max_y] correctly enforces valid probabilities.
    
    Returns: (calibrated_test_probs, fitted_isotonic_model)
    """
    ir = IsotonicRegression(out_of_bounds="clip", increasing=True)
    ir.fit(raw_probs_cal, y_cal)
    calibrated = ir.predict(raw_probs_test)
    return calibrated, ir


def platt_calibrate(
    raw_probs_cal: np.ndarray,
    y_cal: np.ndarray,
    raw_probs_test: np.ndarray
) -> tuple[np.ndarray, dict]:
    """
    Platt scaling via MLE on calibration set.
    Kept for comparison and as fallback.
    """
    def neg_log_likelihood(params, scores, labels):
        A, B = params
        p = 1 / (1 + np.exp(A * scores + B))
        p = np.clip(p, 1e-10, 1 - 1e-10)
        return -np.sum(labels * np.log(p) + (1 - labels) * np.log(1 - p))

    result = minimize(
        neg_log_likelihood, x0=[-1.0, 0.0],
        args=(raw_probs_cal, y_cal), method="L-BFGS-B"
    )
    A_opt, B_opt = result.x
    calibrated = 1 / (1 + np.exp(A_opt * raw_probs_test + B_opt))
    return calibrated, {"method": "platt", "A": float(A_opt), "B": float(B_opt)}


def select_best_calibrator(
    raw_probs_cal: np.ndarray,
    y_cal: np.ndarray,
    raw_probs_val: np.ndarray,
    y_val: np.ndarray
) -> tuple[object, str, float]:
    """
    Compare Platt vs Isotonic on a validation split.
    Select whichever achieves lower ECE on the validation set.
    This is the correct model selection procedure for calibrators.
    
    After selection, refits the chosen model on the FULL calibration
    dataset (train + val) to maximize data efficiency.
    
    Returns: (best_calibrator, method_name, best_ece)
    """
    # Isotonic
    ir = IsotonicRegression(out_of_bounds="clip", increasing=True)
    ir.fit(raw_probs_cal, y_cal)
    p_iso = ir.predict(raw_probs_val)
    ece_iso = compute_ece(p_iso, y_val)

    # Platt
    p_platt, platt_params = platt_calibrate(raw_probs_cal, y_cal, raw_probs_val)
    ece_platt = compute_ece(p_platt, y_val)

    logger.info(f"Calibration ECE — Isotonic: {ece_iso:.4f}, Platt: {ece_platt:.4f}")

    # Combine full cal set for final refit
    full_raw = np.concatenate([raw_probs_cal, raw_probs_val])
    full_y = np.concatenate([y_cal, y_val])

    if ece_iso <= ece_platt:
        logger.info("Selected: Isotonic Regression")
        # Refit isotonic on full cal set
        ir_final = IsotonicRegression(out_of_bounds="clip", increasing=True)
        ir_final.fit(full_raw, full_y)
        return ir_final, "isotonic", ece_iso
    else:
        logger.info("Selected: Platt Scaling")
        # Refit platt on full cal set
        _, params = platt_calibrate(full_raw, full_y, full_raw)
        return params, "platt", ece_platt


def compute_ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = 15) -> float:
    """
    ECE with 15 equal-width bins (more resolution than default 10).
    ECE = Σ_b (|B_b|/n) * |acc(B_b) - conf(B_b)|
    
    Bins with 0 samples are skipped. The sum of (|B_b|/n) over 
    all non-empty bins is exactly 1.0, which is mathematically correct.
    """
    bin_edges = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    n = len(probs)
    for i in range(n_bins):
        mask = (probs >= bin_edges[i]) & (probs < bin_edges[i + 1])
        if mask.sum() == 0:
            continue
        bin_conf = probs[mask].mean()
        bin_acc = labels[mask].mean()
        ece += (mask.sum() / n) * abs(bin_acc - bin_conf)
    return float(ece)


def plot_reliability_diagram(
    raw_probs: np.ndarray,
    calibrated_probs: np.ndarray,
    y_true: np.ndarray,
    method_name: str,
    save_path: str
):
    """Reliability diagram comparing raw vs calibrated probabilities."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    try:
        for probs, label, color, ax in [
            (raw_probs, "Raw ensemble", "#E24B4A", ax1),
            (calibrated_probs, f"Calibrated ({method_name})", "#1D9E75", ax1),
        ]:
            frac_pos, mean_pred = calibration_curve(y_true, probs, n_bins=15)
            ece = compute_ece(probs, y_true)
            ax.plot(mean_pred, frac_pos, "o-", label=f"{label} (ECE={ece:.4f})",
                    color=color)

        ax1.plot([0, 1], [0, 1], "k--", linewidth=0.8, label="Perfect calibration")
        ax1.set_xlabel("Mean predicted probability")
        ax1.set_ylabel("Fraction of positives")
        ax1.set_title("Reliability Diagram")
        ax1.legend(fontsize=8)
        ax1.grid(True, alpha=0.3)

        # Histogram of calibrated probabilities
        ax2.hist(calibrated_probs, bins=30, edgecolor="white", color="#1D9E75", alpha=0.8)
        ax2.set_xlabel("Calibrated probability")
        ax2.set_ylabel("Count")
        ax2.set_title("Distribution of Calibrated Scores")
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        plt.savefig(save_path, dpi=150, bbox_inches="tight")
        logger.info(f"Reliability diagram saved: {save_path}")
    finally:
        plt.close(fig)
