import numpy as np
from typing import Tuple

class ConformalPredictor:
    """
    Split conformal prediction using the nonconformity score:
        α_i = 1 - ŷ_i  (for positive class)
    
    Coverage guarantee (Venn-Abers theorem):
        P(y ∈ C(x)) ≥ 1 - α  for any α ∈ (0,1)
    """
    
    def __init__(self, alpha: float = 0.10):
        """alpha = miscoverage rate. 0.10 → 90% coverage guarantee."""
        self.alpha = alpha
        self.q_hat = None  # quantile threshold
    
    def calibrate(self, 
                  cal_probs: np.ndarray, 
                  cal_labels: np.ndarray) -> float:
        """Compute the (1-alpha) quantile of nonconformity scores."""
        scores = np.where(
            cal_labels == 1,
            1 - cal_probs,   # true repayers: penalise low confidence
            cal_probs        # true defaulters: penalise high confidence
        )
        n = len(cal_labels)
        level = np.ceil((n + 1) * (1 - self.alpha)) / n
        level = min(level, 1.0)
        self.q_hat = float(np.quantile(scores, level))
        return self.q_hat
    
    def predict_interval(self, probs: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Returns (lower_bound, upper_bound) with probability ≥ 1 - alpha."""
        if self.q_hat is None:
            raise RuntimeError("Must call calibrate() before predict_interval()")
        lower = np.clip(probs - self.q_hat, 0, 1)
        upper = np.clip(probs + self.q_hat, 0, 1)
        return lower, upper
    
    def coverage_check(self, 
                       test_probs: np.ndarray, 
                       test_labels: np.ndarray) -> dict:
        """Verify empirical coverage matches theoretical guarantee."""
        lower, upper = self.predict_interval(test_probs)
        # Using labels as proxy for true probability in interval
        # In classification, we check if the label 1 is in the set of classes
        # But here we are doing intervals on probabilities. 
        # Standard conformal prediction for classification would be set-valued.
        # Here we follow the provided logic.
        in_interval = (test_labels >= lower) & (test_labels <= upper)
        empirical_coverage = float(in_interval.mean())
        return {
            "theoretical_coverage": 1 - self.alpha,
            "empirical_coverage": empirical_coverage,
            "q_hat": self.q_hat,
            "avg_interval_width": float((upper - lower).mean()),
            "coverage_satisfied": empirical_coverage >= (1 - self.alpha)
        }
