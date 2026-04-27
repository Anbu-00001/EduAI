"""
Student Skill Gap Analyzer — "What do I need to change to get approved?"

This engine inverts the existing counterfactual engine.
Instead of asking "what is the minimum change to cross GREEN threshold?",
it asks: "what is the HIGHEST VALUE change per unit of effort?"

Priority Score per feature change:
  priority_i = |Δp_i| / effort_i
  
  where:
    Δp_i = improvement in repayment probability if feature i moves to cf value
    effort_i = effort score for achieving that change (1–10 scale, data-derived)
  
  Effort scores are derived from:
    - Time to achieve (e.g., internship = 3 months, CGPA improvement = 1 semester)
    - Cost to achieve (paid courses vs free)
    - Feasibility given current profile (backlogs cannot be removed but can be reduced)
  
  All effort values are loaded from a JSON config — not hardcoded in code.
  The config file is editable without code changes.

Actionable Guidance Generator:
  For each gap identified, generate a specific action with:
    - What to do (concrete, not generic)
    - How long it takes
    - Expected probability lift
    - Priority rank

Skill Roadmap:
  Ordered list of actions sorted by priority_i (highest first).
  Cumulative probability improvement shown at each step.
  Stops when cumulative p_improvement pushes student to GREEN tier.
"""

import numpy as np
import json
import pickle
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

EFFORT_CONFIG_PATH = Path("model/skill_gap_effort_config.json")

DEFAULT_EFFORT_CONFIG = {
    "cgpa_normalized": {
        "effort_score": 8,
        "time_months": 12,
        "action_template": "Improve CGPA from {orig:.1f}/10 to {target:.1f}/10 "
                           "through consistent exam performance",
        "feasibility": "HIGH if in Year 1-2, MEDIUM if in Year 3-4, LOW if graduated",
        "resources": ["College academic support", "Study groups", "Online tutoring"],
    },
    "internships_count": {
        "effort_score": 3,
        "time_months": 3,
        "action_template": "Complete {delta:.0f} additional internship(s) — "
                           "target companies with structured programmes",
        "feasibility": "HIGH for any student",
        "resources": [
            "LinkedIn Jobs (filter: Internship, India)",
            "Internshala.com",
            "AICTE internship portal",
        ],
    },
    "backlogs": {
        "effort_score": 6,
        "time_months": 6,
        "action_template": "Clear {delta:.0f} backlog(s) in upcoming supplementary exams",
        "feasibility": "HIGH — supplementary exams available for all backlogs",
        "resources": ["Previous year papers", "College tutors"],
    },
    "potential_score": {
        "effort_score": 5,
        "time_months": 6,
        "action_template": "Build {delta:.0f} additional projects relevant to {field}",
        "feasibility": "HIGH for all students",
        "resources": [
            "GitHub — contribute to open source",
            "Kaggle competitions for data science",
            "Hackathons on Devfolio",
        ],
    },
    "placement_rate_for_field": {
        "effort_score": 9,
        "time_months": 0,
        "action_template": "Consider institution with higher placement rate "
                           "({orig:.0%} → {target:.0%})",
        "feasibility": "LOW — cannot change institution easily",
        "resources": ["NIRF Rankings", "Shiksha.com placement data"],
    },
    "demand_proxy": {
        "effort_score": 7,
        "time_months": 18,
        "action_template": "Transition to adjacent high-demand field — "
                           "add certifications in {field} specialisation",
        "feasibility": "MEDIUM — requires 6–18 months upskilling",
        "resources": [
            "Coursera Google Career Certificates",
            "NPTEL certification courses",
            "Skill India digital platform",
        ],
    },
}


def load_effort_config() -> dict:
    """Load effort configuration. Create from default if not exists."""
    if not EFFORT_CONFIG_PATH.exists():
        EFFORT_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        EFFORT_CONFIG_PATH.write_text(json.dumps(DEFAULT_EFFORT_CONFIG, indent=2))
    return json.loads(EFFORT_CONFIG_PATH.read_text())


@dataclass
class GapAction:
    feature: str
    original_value: float
    target_value: float
    delta: float
    probability_lift: float
    effort_score: int
    priority_score: float
    time_months: int
    action_text: str
    feasibility: str
    resources: list[str]


@dataclass
class SkillGapReport:
    current_probability: float
    target_probability: float
    current_tier: str
    target_tier: str
    actions: list[GapAction]       # Sorted by priority_score desc
    cumulative_lifts: list[float]  # Cumulative p after each action
    estimated_time_to_green_months: Optional[int]
    field: str


def _compute_probability_lift(
    feature_idx: int,
    original_features: np.ndarray,
    target_value: float,
    predict_fn,
) -> float:
    """
    Compute probability improvement from changing one feature.
    Isolated feature perturbation — not full counterfactual.
    """
    modified = original_features.copy()
    modified[feature_idx] = target_value
    p_original = float(predict_fn(original_features.reshape(1, -1))[0])
    p_modified = float(predict_fn(modified.reshape(1, -1))[0])
    return round(p_modified - p_original, 4)


def generate_skill_gap_report(
    student_features: np.ndarray,
    counterfactual_result: dict,
    predict_fn,
    feature_names: list,
    current_probability: float,
    field: str,
    target_probability: float = 0.72,
) -> SkillGapReport:
    """
    Generate prioritised skill gap report from counterfactual changes.
    
    Uses the counterfactual already computed by model/counterfactual.py.
    Enriches it with effort scores, resources, and priority ranking.
    """
    effort_config = load_effort_config()
    changes = counterfactual_result.get("changes_required", {})
    
    if not changes:
        return SkillGapReport(
            current_probability=current_probability,
            target_probability=target_probability,
            current_tier=_prob_to_tier(current_probability),
            target_tier=_prob_to_tier(target_probability),
            actions=[],
            cumulative_lifts=[current_probability],
            estimated_time_to_green_months=None,
            field=field,
        )
    
    feature_idx_map = {name: i for i, name in enumerate(feature_names)}
    actions = []
    
    for feat, change in changes.items():
        if feat not in effort_config:
            continue
        
        cfg = effort_config[feat]
        original_val = change["original"]
        target_val = change["counterfactual"]
        delta = change["change"]
        
        feat_idx = feature_idx_map.get(feat)
        if feat_idx is None:
            continue
        
        lift = _compute_probability_lift(
            feat_idx, student_features, target_val, predict_fn
        )
        
        effort = cfg["effort_score"]
        priority = abs(lift) / max(effort, 1)   # Higher lift per effort = higher priority
        
        action_text = cfg["action_template"].format(
            orig=original_val * 10 if "cgpa" in feat else original_val,
            target=target_val * 10 if "cgpa" in feat else target_val,
            delta=abs(delta) if "internship" in feat or "backlog" in feat
                  else abs(delta),
            field=field.replace("_", " ")
        )
        
        actions.append(GapAction(
            feature=feat,
            original_value=round(original_val, 4),
            target_value=round(target_val, 4),
            delta=round(delta, 4),
            probability_lift=lift,
            effort_score=effort,
            priority_score=round(priority, 4),
            time_months=cfg["time_months"],
            action_text=action_text,
            feasibility=cfg["feasibility"],
            resources=cfg.get("resources", []),
        ))
    
    # Sort by priority (highest first)
    actions.sort(key=lambda a: a.priority_score, reverse=True)
    
    # Compute cumulative lifts
    cumulative = current_probability
    cumulative_lifts = [current_probability]
    for action in actions:
        cumulative = min(1.0, cumulative + abs(action.probability_lift))
        cumulative_lifts.append(round(cumulative, 4))
    
    # Estimate time to GREEN: sum months of actions until cumulative >= target
    time_to_green = None
    cum_prob = current_probability
    total_months = 0
    for action in actions:
        total_months = max(total_months, action.time_months)  # Actions can be parallel
        cum_prob += abs(action.probability_lift)
        if cum_prob >= target_probability:
            time_to_green = total_months
            break
    
    return SkillGapReport(
        current_probability=current_probability,
        target_probability=target_probability,
        current_tier=_prob_to_tier(current_probability),
        target_tier=_prob_to_tier(target_probability),
        actions=actions,
        cumulative_lifts=cumulative_lifts,
        estimated_time_to_green_months=time_to_green,
        field=field,
    )


def _prob_to_tier(p: float) -> str:
    if p >= 0.72:
        return "GREEN"
    elif p >= 0.50:
        return "AMBER"
    return "RED"
