from sklearn.calibration import calibration_curve
import matplotlib.pyplot as plt
import numpy as np
import os, json

def platt_scale(ensemble_probs_train: np.ndarray, 
                y_train: np.ndarray,
                ensemble_probs_test: np.ndarray,
                method: str = "isotonic") -> tuple[np.ndarray, dict]:
    """
    Calibrate probabilities using either Platt Scaling or Isotonic Regression.
    """
    if method == "isotonic":
        # use IsotonicRegression
        from sklearn.isotonic import IsotonicRegression
        ir = IsotonicRegression(out_of_bounds='clip')
        ir.fit(ensemble_probs_train, y_train)
        calibrated_probs = ir.predict(ensemble_probs_test)
        # For saving, we'll store the model or a simplified version
        # Since we can't easily JSON serialize IsotonicRegression, we'll use a lookup table
        bins = np.linspace(0, 1, 101)
        lookup = ir.predict(bins)
        return calibrated_probs, {"method": "isotonic", "bins": bins.tolist(), "lookup": lookup.tolist()}
    else:
        # Platt Scaling
        from scipy.optimize import minimize
        def neg_log_likelihood(params, scores, labels):
            A, B = params
            p = 1 / (1 + np.exp(A * scores + B))
            p = np.clip(p, 1e-10, 1 - 1e-10)
            return -np.sum(labels * np.log(p) + (1 - labels) * np.log(1 - p))
        
        result = minimize(neg_log_likelihood, x0=[-1.0, 0.0], args=(ensemble_probs_train, y_train))
        A_opt, B_opt = result.x
        calibrated_probs = 1 / (1 + np.exp(A_opt * ensemble_probs_test + B_opt))
        return calibrated_probs, {"method": "platt", "A": float(A_opt), "B": float(B_opt)}

def compute_ece(probs: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
    """
    Expected Calibration Error: ECE = Σ_b (|B_b|/n) * |acc(B_b) - conf(B_b)|
    Perfect calibration: ECE = 0.0
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

def plot_calibration_curve(raw_probs, calibrated_probs, y_true, save_path):
    """Reliability diagram: perfect calibration = diagonal line."""
    fig, ax = plt.subplots(figsize=(8, 6))
    
    for probs, label, color in [
        (raw_probs, "Raw ensemble", "#E24B4A"),
        (calibrated_probs, "Platt-scaled", "#1D9E75"),
    ]:
        frac_pos, mean_pred = calibration_curve(y_true, probs, n_bins=10)
        ece = compute_ece(probs, y_true)
        ax.plot(mean_pred, frac_pos, "o-", label=f"{label} (ECE={ece:.4f})", color=color)
    
    ax.plot([0, 1], [0, 1], "k--", linewidth=0.8, label="Perfect calibration")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Fraction of positives (actual repayment rate)")
    ax.set_title("Reliability Diagram — EduPredict AI Probability Calibration")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close()
