"""
EduPredict AI — Central Configuration

ALL values that control system behaviour live here.
Nothing is hardcoded in any other file.

Values with (*) are loaded from environment variables.
Values without (*) are computed from data at runtime or from
domain-documented constants (documented with source citation).

RULE: if a value appears in more than one file, it belongs here.
"""

import os
import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)


# ── Paths ──────────────────────────────────────────────────────────────────
ROOT_DIR          = Path(__file__).parent
DATA_DIR          = ROOT_DIR / "data"
RAW_DIR           = DATA_DIR / "raw"
PROCESSED_DIR     = DATA_DIR / "processed"
PIPELINE_DIR      = DATA_DIR / "pipeline"
HISTORY_DIR       = PIPELINE_DIR / "history"
ARTIFACTS_DIR     = ROOT_DIR / "model" / "artifacts"
MONITORING_DB     = DATA_DIR / "monitoring.db"
MLFLOW_DB         = ROOT_DIR / "mlflow.db"

# Ensure all directories exist on import
for _dir in [RAW_DIR, PROCESSED_DIR, PIPELINE_DIR, HISTORY_DIR, ARTIFACTS_DIR]:
    _dir.mkdir(parents=True, exist_ok=True)


# ── Environment Variables ──────────────────────────────────────────────────
class EnvConfig:
    """
    All environment variables in one place.
    Raises clear errors if required variables are missing.
    Documents what each variable does and where it comes from.
    """

    @staticmethod
    def require(key: str, description: str) -> str:
        val = os.environ.get(key)
        if not val:
            raise EnvironmentError(
                f"Required environment variable '{key}' is not set.\n"
                f"Purpose: {description}\n"
                f"Set it with: export {key}=<value>"
            )
        return val

    @staticmethod
    def optional(key: str, default: str, description: str) -> str:
        val = os.environ.get(key, default)
        if val == default:
            logger.debug(f"Using default for {key}={default!r} ({description})")
        return val

    # Required
    JWT_SECRET = lambda: EnvConfig.require(
        "JWT_SECRET",
        "Secret key for JWT token signing. Generate with: python -c \"import secrets; print(secrets.token_hex(32))\""
    )

    # Optional with documented defaults
    DATABASE_URL = lambda: EnvConfig.optional(
        "DATABASE_URL",
        "postgresql://edupredict:edupredict@localhost:5432/edupredict",
        "PostgreSQL connection string"
    )
    REDIS_URL = lambda: EnvConfig.optional(
        "REDIS_URL", "redis://localhost:6379/0",
        "Redis connection for rate limiting"
    )
    DATAGOV_API_KEY = lambda: EnvConfig.optional(
        "DATAGOV_API_KEY", "",
        "data.gov.in API key — register free at data.gov.in/user/register"
    )
    MLFLOW_TRACKING_URI = lambda: EnvConfig.optional(
        "MLFLOW_TRACKING_URI", f"sqlite:///{MLFLOW_DB}",
        "MLflow experiment tracking database URI"
    )
    DPO_EMAIL = lambda: EnvConfig.optional(
        "DPO_EMAIL", "dpo@edupredict.ai",
        "Data Protection Officer email for DPDP Act compliance"
    )

    # RBI macro indicators — documented public sources
    # Source: RBI Monetary Policy Statement, April 2025
    RBI_REPO_RATE = lambda: float(EnvConfig.optional(
        "RBI_REPO_RATE", "0.0625",
        "RBI repo rate. Source: RBI monetary policy press release. Update quarterly."
    ))
    # Source: MOSPI CPI Index, Education component, March 2025
    CPI_EDUCATION = lambda: float(EnvConfig.optional(
        "CPI_EDUCATION", "0.051",
        "CPI education inflation. Source: MOSPI CPI data. Update quarterly."
    ))

    DAG_INTERVAL_HOURS = lambda: float(EnvConfig.optional(
        "DAG_INTERVAL_HOURS", "6",
        "How often the data acquisition DAG runs (hours)"
    ))
    DAG_CACHE_MAX_AGE_HOURS = lambda: float(EnvConfig.optional(
        "DAG_CACHE_MAX_AGE_HOURS", "12",
        "Maximum age of demand cache before forcing refresh (hours)"
    ))
    RATE_LIMIT_DEFAULT_RPM = lambda: int(EnvConfig.optional(
        "RATE_LIMIT_DEFAULT_RPM", "100",
        "Default API rate limit (requests per minute) for new tenants"
    ))

    # CORS
    ALLOWED_ORIGINS = lambda: EnvConfig.optional(
        "ALLOWED_ORIGINS",
        "http://localhost:3000,http://localhost:5173,http://localhost:8501",
        "Comma-separated allowed CORS origins. Add your production domain in prod."
    )

    # IMRI default when data.gov.in is unreachable
    IMRI_DEFAULT = lambda: float(EnvConfig.optional(
        "IMRI_DEFAULT", "0.72",
        "Fallback India Macro Repayment Index when PLFS API is unreachable. "
        "0.72 = derived from PLFS 2023-24 Q3 values. Update quarterly."
    ))

    # JanParichay (not yet active — placeholder for future integration)
    JANPARICHAY_CLIENT_ID = lambda: EnvConfig.optional(
        "JANPARICHAY_CLIENT_ID", "",
        "MeriPehchaan OAuth2 client ID. Register at jppartners.meripehchaan.gov.in. "
        "Required for DigiLocker academic record auto-fill."
    )
    JANPARICHAY_CLIENT_SECRET = lambda: EnvConfig.optional(
        "JANPARICHAY_CLIENT_SECRET", "",
        "MeriPehchaan OAuth2 client secret. Never commit to git."
    )
    JANPARICHAY_REDIRECT_URI = lambda: EnvConfig.optional(
        "JANPARICHAY_REDIRECT_URI", "http://localhost:8000/v1/auth/callback",
        "OAuth2 redirect URI. Must match exactly what is registered at meripehchaan.gov.in."
    )
    
    PROMETHEUS_URL = lambda: EnvConfig.optional(
        "PROMETHEUS_URL", "http://localhost:9090",
        "Prometheus instance URL for admin metrics proxy"
    )
    GRAFANA_URL = lambda: EnvConfig.optional(
        "GRAFANA_URL", "http://localhost:3000",
        "Grafana instance URL. Linked from admin panel (not embedded)."
    )


# ── Data-Derived Constants (computed at training time, loaded at runtime) ──
class ModelConfig:
    """
    Configuration values that come from training data analysis.
    These are saved to artifacts/ during training and loaded here.
    NEVER hardcoded — always loaded from the artifacts file.
    """

    _cache: Optional[dict] = None

    @classmethod
    def load(cls) -> dict:
        if cls._cache is not None:
            return cls._cache
        metrics_path = ARTIFACTS_DIR / "metrics.json"
        if not metrics_path.exists():
            raise FileNotFoundError(
                f"Model artifacts not found at {metrics_path}.\n"
                f"Run: python model/retrain_with_temporal.py"
            )
        cls._cache = json.loads(metrics_path.read_text())
        return cls._cache

    @classmethod
    def feature_cols(cls) -> list[str]:
        return cls.load().get("feature_cols_v3", [])

    @classmethod
    def model_version(cls) -> str:
        return cls.load().get("model_version", "unknown")

    @classmethod
    def graph_alpha(cls) -> float:
        path = ARTIFACTS_DIR / "graph_params.json"
        if not path.exists():
            logger.warning("graph_params.json not found — using alpha=1.0 (model only)")
            return 1.0
        return float(json.loads(path.read_text())["alpha"])

    @classmethod
    def conformal_q_hat(cls) -> float:
        path = ARTIFACTS_DIR / "conformal_params.json"
        if not path.exists():
            raise FileNotFoundError("conformal_params.json not found")
        return float(json.loads(path.read_text())["q_hat"])

    @classmethod
    def calibration_params(cls) -> dict:
        path = ARTIFACTS_DIR / "calibration_params.json"
        if not path.exists():
            raise FileNotFoundError("calibration_params.json not found")
        return json.loads(path.read_text())

    @classmethod
    def feature_ranges(cls) -> dict:
        path = ARTIFACTS_DIR / "feature_ranges.json"
        if not path.exists():
            raise FileNotFoundError("feature_ranges.json not found")
        return json.loads(path.read_text())


# ── Domain Constants (documented with source citations) ──────────────────
class DomainConstants:
    """
    Domain knowledge constants that are stable and well-documented.
    Every value has a source citation.
    These are NOT hardcoded thresholds — they are documented facts.
    """

    # Source: RBI FSR June 2024 — education loan NPA rate
    EDUCATION_LOAN_INDUSTRY_NPA_RATE = 0.036

    # Source: ILO India Employment Report 2024
    GRADUATE_UNEMPLOYMENT_RATE_INDIA = 0.137

    # Source: PLFS 2023-24, MoSPI
    INDIA_OVERALL_UNEMPLOYMENT_RATE = 0.032

    # Source: India Skills Report 2025 (Wheebox/CII)
    GRADUATE_EMPLOYABILITY_RATE = 0.45

    # Source: Glassdoor/AmbitionBox India salary data 2024-25
    # These are approximate salary ranges for normalisation — not exact
    FIELD_SALARY_MIN_INR = 300_000    # ₹3L — civil/biotech fresh grad floor
    FIELD_SALARY_MAX_INR = 2_500_000  # ₹25L — top CS/AI grads

    # Source: RBI NBFC lending guidelines, FOIR norms
    EMI_TO_SALARY_SAFE_THRESHOLD = 0.30    # Below this: SAFE
    EMI_TO_SALARY_CAUTION_THRESHOLD = 0.50  # Above this: DEBT_TRAP_RISK
    # NOTE: These thresholds are overridden at runtime by training data
    # distribution quantiles when sufficient data is available.
    # See loan_roi.py compute_loan_roi() for runtime computation.

    # Source: RBI Circular on MCLR, typical NBFC education loan rates 2024-25
    TYPICAL_EDUCATION_LOAN_RATE = 0.105   # 10.5% annual

    # Source: RBI standard repayment tenure for education loans
    TYPICAL_TENURE_YEARS = 7

    # Source: NIRF ranking methodology documentation
    NIRF_PLACEMENT_RATE_STRONG = 0.85    # Above this: strong institution
    NIRF_PLACEMENT_RATE_MODERATE = 0.60  # Above this: moderate institution

    # Source: Upstart model card, adapted for India context
    CONFORMAL_MISCOVERAGE_RATE = 0.10    # 90% coverage guarantee

    # Source: US ECOA "80% rule", adopted in RBI FREE-AI Framework August 2025
    FAIRNESS_DPI_MINIMUM = 0.80

    # Source: Basel II/III credit risk modelling literature
    PSI_MONITOR_THRESHOLD = 0.10    # Above this: monitor feature
    PSI_RETRAIN_THRESHOLD = 0.25    # Above this: retrain model

    # Source: GDPR Article 4 + DPDP Act Section 2 + RBI KYC guidelines
    CONSENT_NOTICE_VERSION = "1.1"

    # Source: Industry standard for ML model promotion gates
    AUC_PROMOTION_MINIMUM = 0.78
    ECE_PROMOTION_MAXIMUM = 0.05

FIELD_QUERIES = {
    "computer_science": "computer science engineer",
    "data_science": "data scientist machine learning",
    "mba_finance": "MBA finance analyst",
    "mechanical_engineering": "mechanical engineer",
    "electrical_engineering": "electrical engineer",
    "civil_engineering": "civil engineer",
    "biotechnology": "biotechnology life sciences",
}

SOURCE_DECAY = {
    "naukri": 0.020,
    "linkedin": 0.020,
    "datagov": 0.001
}

SOURCE_WEIGHTS = {
    "naukri":  0.45,
    "linkedin": 0.45,
    "datagov": 0.10,
}
