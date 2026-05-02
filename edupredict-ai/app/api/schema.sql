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

CREATE TABLE IF NOT EXISTS consent_records (
    id SERIAL PRIMARY KEY,
    consent_id VARCHAR(64) UNIQUE NOT NULL,
    user_hash VARCHAR(64) NOT NULL,
    consent_given BOOLEAN NOT NULL,
    notice_version VARCHAR(10) NOT NULL,
    data_sources JSONB NOT NULL,
    ip_hash VARCHAR(16),
    user_agent_hash VARCHAR(16),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_consent_user ON consent_records(user_hash, created_at DESC);

CREATE TABLE IF NOT EXISTS api_calls (
    id SERIAL PRIMARY KEY,
    assessment_id UUID NOT NULL,
    features_json JSONB NOT NULL,
    prediction FLOAT NOT NULL,
    risk_tier VARCHAR(10) NOT NULL,
    api_key_id VARCHAR(64),
    latency_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_api_calls_time ON api_calls(created_at DESC);

CREATE TABLE IF NOT EXISTS api_keys (
    id SERIAL PRIMARY KEY,
    tenant_id VARCHAR(64) NOT NULL,
    key_hash VARCHAR(64) UNIQUE NOT NULL,
    rate_limit_rpm INTEGER NOT NULL DEFAULT 100,
    permissions JSONB NOT NULL DEFAULT '["assess"]'::jsonb,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_api_keys_tenant ON api_keys(tenant_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash   ON api_keys(key_hash) WHERE active = TRUE;

