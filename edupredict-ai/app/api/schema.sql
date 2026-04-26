CREATE TABLE IF NOT EXISTS assessments (
    id UUID PRIMARY KEY,
    profile_data JSONB NOT NULL,
    calibrated_probability FLOAT NOT NULL,
    risk_tier VARCHAR(10) NOT NULL,
    shap_values JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_assessments_risk_tier ON assessments(risk_tier);
CREATE INDEX idx_assessments_created_at ON assessments(created_at);
CREATE INDEX idx_assessments_prob ON assessments(calibrated_probability);

CREATE TABLE IF NOT EXISTS model_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_type VARCHAR(50) NOT NULL,
    auc_score FLOAT,
    ece_score FLOAT,
    conformal_coverage FLOAT,
    fairness_dpi FLOAT,
    artifact_path TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
