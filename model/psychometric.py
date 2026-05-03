from dataclasses import dataclass
from typing import List


@dataclass
class PsychometricOption:
    label: str
    text: str
    score: float


@dataclass
class PsychometricQuestion:
    id: int
    question: str
    category: str
    options: List[PsychometricOption]


PSYCHOMETRIC_QUESTIONS: List[PsychometricQuestion] = [
    PsychometricQuestion(
        id=1,
        question="How do you manage your monthly finances?",
        category="Financial Discipline",
        options=[
            PsychometricOption("A", "I track every expense and maintain a strict budget", 1.0),
            PsychometricOption("B", "I have a rough budget but don't track closely", 0.5),
            PsychometricOption("C", "I spend first and try to save what's left", 0.25),
            PsychometricOption("D", "I don't actively track my spending", 0.0),
        ],
    ),
    PsychometricQuestion(
        id=2,
        question="Where do you see yourself professionally in 3 years?",
        category="Career Clarity",
        options=[
            PsychometricOption("A", "Clear target role at a specific company or sector", 1.0),
            PsychometricOption("B", "I know the industry, flexible on the exact role", 0.5),
            PsychometricOption("C", "Still exploring options", 0.25),
            PsychometricOption("D", "No specific professional plan yet", 0.0),
        ],
    ),
    PsychometricQuestion(
        id=3,
        question="When you face a major academic or professional setback, you typically:",
        category="Resilience",
        options=[
            PsychometricOption("A", "Analyse what went wrong and adapt immediately", 1.0),
            PsychometricOption("B", "Take some time to process, then recover with a plan", 0.5),
            PsychometricOption("C", "Need significant external support to get back on track", 0.25),
            PsychometricOption("D", "Find it difficult to recover for an extended period", 0.0),
        ],
    ),
    PsychometricQuestion(
        id=4,
        question="When you need to learn a new skill required for your career, you:",
        category="Learning Agility",
        options=[
            PsychometricOption("A", "Start within a week — set a deadline and complete it", 1.0),
            PsychometricOption("B", "Start within a month after researching options", 0.5),
            PsychometricOption("C", "Wait for a formal course or enrollment opportunity", 0.25),
            PsychometricOption("D", "Usually wait until pushed by external circumstances", 0.0),
        ],
    ),
    PsychometricQuestion(
        id=5,
        question="If you faced unexpected job loss, your EMI repayment plan would be:",
        category="Financial Resilience",
        options=[
            PsychometricOption("A", "I have / plan to build a 6+ month emergency fund", 1.0),
            PsychometricOption("B", "I have / plan to build a 3-month emergency fund", 0.5),
            PsychometricOption("C", "Family or co-applicant would cover temporarily", 0.25),
            PsychometricOption("D", "I haven't planned for this scenario yet", 0.0),
        ],
    ),
]


@dataclass
class PsychometricResult:
    raw_score: float
    normalized_score: float
    adjustment: float
    profile_type: str
    insight: str


def score_psychometric(answers: List[float]) -> PsychometricResult:
    """
    Score 5 psychometric answers (each 0.0, 0.25, 0.5, or 1.0).
    Returns a post-hoc calibration adjustment in [-0.05, +0.05].
    Does NOT modify the frozen feature vector — purely additive on calibrated_probability.
    """
    if len(answers) != 5:
        raise ValueError(f"Expected 5 answers, got {len(answers)}")

    raw_score = sum(answers)
    normalized = raw_score / 5.0  # maps to [0, 1]

    # Linear: normalized=0.5 → 0.0 adj; normalized=1.0 → +0.05; normalized=0.0 → -0.05
    adjustment = round((normalized - 0.5) * 0.10, 4)
    adjustment = max(-0.05, min(0.05, adjustment))

    if normalized >= 0.80:
        profile_type = "High Financial Resilience"
        insight = (
            "Your strong financial habits and career clarity significantly reduce lender risk. "
            "This profile correlates with high repayment rates in RBI micro-lending data."
        )
    elif normalized >= 0.60:
        profile_type = "Developing Financial Discipline"
        insight = (
            "You show solid foundations but have room to strengthen your financial safety net. "
            "Focus on building an emergency fund covering at least 3 EMIs before disbursement."
        )
    elif normalized >= 0.40:
        profile_type = "Moderate Risk Awareness"
        insight = (
            "You are aware of financial risks but need more structure. "
            "Consider NPTEL's Personal Finance course and start an expense tracker before taking on debt."
        )
    else:
        profile_type = "Building Financial Foundation"
        insight = (
            "Current financial habits may increase repayment risk. "
            "Work with a financial counsellor and build a 90-day budget plan before borrowing."
        )

    return PsychometricResult(
        raw_score=raw_score,
        normalized_score=round(normalized, 4),
        adjustment=adjustment,
        profile_type=profile_type,
        insight=insight,
    )
