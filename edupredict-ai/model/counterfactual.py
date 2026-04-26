import numpy as np
import pandas as pd
from scipy.optimize import minimize

def find_counterfactual(
        student_features: np.ndarray,
        model_predict_fn,       # callable: features → probability
        feature_names: list,
        feature_ranges: dict,   # {feature_name: (min, max)} from training data
        target_prob: float = 0.70,
        lambda_proximity: float = 0.95
) -> dict:
    """
    Finds the minimal-change counterfactual: the closest point in 
    feature space where the model predicts probability ≥ target_prob.
    
    Objective (Wachter et al., 2017):
        min_{x'} λ * L_pred(x') + (1-λ) * d(x, x')
    """
    x = student_features.copy().astype(float).flatten()
    
    # Compute feature std from ranges for normalization
    feature_stds = {
        k: (v[1] - v[0]) / 4.0 if (v[1] - v[0]) > 0 else 0.1
        for k, v in feature_ranges.items()
    }
    
    def objective(x_prime):
        pred_loss = (model_predict_fn(x_prime.reshape(1, -1))[0] - target_prob) ** 2
        proximity = sum(
            abs(x_prime[i] - x[i]) / max(feature_stds[feature_names[i]], 1e-6)
            for i in range(len(feature_names))
        )
        return lambda_proximity * pred_loss + (1 - lambda_proximity) * proximity
    
    bounds = [(feature_ranges[f][0], feature_ranges[f][1]) for f in feature_names]
    
    result = minimize(
        objective,
        x0=x.copy(),
        method="L-BFGS-B",
        bounds=bounds,
        options={"maxiter": 1000, "ftol": 1e-8}
    )
    
    x_cf = result.x
    cf_prob = model_predict_fn(x_cf.reshape(1, -1))[0]
    
    changes = {}
    for i, fname in enumerate(feature_names):
        delta = x_cf[i] - x[i]
        if abs(delta) > 0.01:
            changes[fname] = {
                "original": round(float(x[i]), 4),
                "counterfactual": round(float(x_cf[i]), 4),
                "change": round(float(delta), 4),
                "direction": "increase" if delta > 0 else "decrease"
            }
    
    return {
        "original_probability": float(model_predict_fn(x.reshape(1, -1))[0]),
        "counterfactual_probability": round(float(cf_prob), 4),
        "target_probability": target_prob,
        "achieved": cf_prob >= target_prob,
        "changes_required": changes,
        "num_features_changed": len(changes)
    }
