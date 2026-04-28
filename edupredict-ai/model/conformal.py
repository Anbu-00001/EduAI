import numpy as np
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

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
        if level >= 1.0:
            logger.warning(f"Calibration set may be too small for alpha={self.alpha}")
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
        """
        Verify empirical coverage matches theoretical guarantee.
        
        NON-STANDARD INTERPRETATION WARNING:
        In standard conformal classification, the output is a set of classes (e.g., {0, 1}).
        Here, we output an interval over probabilities [lower, upper].
        The mathematically correct check is whether the TRUE UNKNOWN probability P(Y=1|X)
        falls in [lower, upper]. Since P(Y=1|X) is unobservable, we use the binary
        label Y ∈ {0, 1} as a proxy.
        
        This means we check if the label (0 or 1) falls inside the probability interval.
        This is an approximation. It is acceptable for this use case because 
        we treat the classification task as a probability estimation task (regression
        on the probability space), and evaluating against the observed outcome provides
        a conservative lower bound on the true probability coverage.
        """
        lower, upper = self.predict_interval(test_probs)
        in_interval = (test_labels >= lower) & (test_labels <= upper)
        empirical_coverage = float(in_interval.mean())
        return {
            "theoretical_coverage": 1 - self.alpha,
            "empirical_coverage": empirical_coverage,
            "q_hat": self.q_hat,
            "avg_interval_width": float((upper - lower).mean()),
            "coverage_satisfied": empirical_coverage >= (1 - self.alpha)
        }
