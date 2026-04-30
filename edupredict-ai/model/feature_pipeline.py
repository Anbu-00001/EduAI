from dataclasses import dataclass
import numpy as np
from typing import Optional

FEATURE_COLS = [
    "cgpa_normalized", "internships_count", "backlogs",
    "median_salary_normalized", "potential_score", "demand_proxy",
    "placement_rate_for_field", "demand_velocity_per_day",
    "demand_acceleration", "velocity_r_squared", "demand_momentum",
    "market_hhi", "macro_index", "backlogs_missing"
]

@dataclass
class TemporalFeatures:
    velocity: float = 0.0
    accel: float = 0.0
    r2: float = 0.0
    estimated: bool = True

@dataclass
class MarketFeatures:
    demand_proxy: float = 0.5
    market_hhi: float = 0.143
    macro_index: float = 0.72

class FeaturePipeline:
    """
    Single transform path for both training and inference.
    Never instantiate separate logic — import this class everywhere.
    """
    N_FIELDS = 7

    @staticmethod
    def compute_potential_score(
        cgpa_norm: float,
        internships_count: int,
        placement_rate_norm: float,
        salary_norm: float,
    ) -> float:
        return (
            0.35 * cgpa_norm
            + 0.25 * np.minimum(internships_count / 3.0, 1.0)
            + 0.25 * placement_rate_norm
            + 0.15 * salary_norm
        )

    @staticmethod
    def compute_momentum(demand_proxy: float, velocity_scaled: float, ewma_halflife_days: float = 2.0) -> float:
        alpha = 1 - np.exp(-np.log(2) / ewma_halflife_days)
        return alpha * velocity_scaled + (1 - alpha) * demand_proxy

    @classmethod
    def transform(
        cls,
        cgpa: float,
        internships_count: int,
        backlogs: int,
        field_of_study: str,
        college_placement_rate: float,
        salary_norm: float,
        temporal: TemporalFeatures,
        market: MarketFeatures,
        backlogs_missing: int = 0,
    ) -> np.ndarray:
        cgpa_norm          = cgpa / 10.0
        placement_rate_norm = college_placement_rate / 100.0
        potential_score    = cls.compute_potential_score(cgpa_norm, internships_count, placement_rate_norm, salary_norm)
        v_scaled           = np.clip((temporal.velocity + 50) / 100, 0, 1)
        momentum           = cls.compute_momentum(market.demand_proxy, v_scaled)

        return np.array([
            cgpa_norm,
            internships_count,
            backlogs,
            salary_norm,
            potential_score,
            market.demand_proxy,
            placement_rate_norm,
            temporal.velocity,
            temporal.accel,
            temporal.r2,
            momentum,
            market.market_hhi,
            market.macro_index,
            backlogs_missing,
        ], dtype=np.float64)

    @classmethod
    def feature_names(cls) -> list[str]:
        return FEATURE_COLS.copy()
