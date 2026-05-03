import re

with open("app/api/main.py", "r") as f:
    content = f.read()

# 1. Imports
content = content.replace("from app.api.rate_limit import check_rate_limit", 
"""from app.api.rate_limit import check_rate_limit, limiter, create_redis_pool
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from model.feature_pipeline import FeaturePipeline, TemporalFeatures, MarketFeatures""")

# 2. Rate limit handler
handler_code = """
async def _rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "detail": f"Too many requests. Limit: {exc.limit}",
            "retry_after_seconds": 60,
        },
        headers={"Retry-After": "60"},
    )

@asynccontextmanager"""
content = content.replace("@asynccontextmanager", handler_code, 1)

# 3. Lifespan redis
content = content.replace("app.state.db_pool = await asyncpg.create_pool(EnvConfig.DATABASE_URL())",
"""app.state.db_pool = await asyncpg.create_pool(EnvConfig.DATABASE_URL())
    app.state.redis = await create_redis_pool()""")
content = content.replace("await app.state.db_pool.close()",
"""await app.state.db_pool.close()
    await app.state.redis.aclose()""")

# 4. FastAPI app
app_code = """app = FastAPI(
    title="EduPredict AI API",
    description="Production-Grade Student Loan Risk Engine",
    version="5.0.0",
    lifespan=lifespan
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)"""
content = content.replace("""app = FastAPI(
    title="EduPredict AI API",
    description="Production-Grade Student Loan Risk Engine",
    version="5.0.0",
    lifespan=lifespan
)""", app_code)

# 5. AssessRequest
request_models = """class ConsentBlock(BaseModel):
    data_sources: List[str]
    notice_version: str = "1.0"

class AssessRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")
    cgpa: float = Field(..., ge=0.0, le=10.0)
    internships_count: int = Field(..., ge=0, le=10)
    backlogs: int = Field(..., ge=0, le=20)
    field_of_study: str = Field(...)
    college_placement_rate: float = Field(..., ge=0.0, le=100.0)
    loan_amount_inr: float = Field(..., ge=10000.0)
    annual_family_income_inr: Optional[float] = Field(None, ge=0)
    user_hash: str
    has_consent: bool
    cgpa_verified: bool = False
    institution_verified: bool = False
    consent: ConsentBlock

    @field_validator("field_of_study")
    @classmethod
    def validate_field(cls, v):
        from config import FIELD_QUERIES
        valid = list(FIELD_QUERIES.keys())
        if v not in valid:
            raise ValueError(f"field_of_study must be one of {valid}")
        return v

    @field_validator("loan_amount_inr")
    @classmethod
    def validate_loan(cls, v):
        if v > 5_000_000:
            raise ValueError("loan_amount_inr capped at ₹50,00,000 for advisory mode")
        return v

class StudentProfile(BaseModel):"""
content = content.replace("class StudentProfile(BaseModel):", request_models)

# 6. Delete build_features
build_features_regex = re.compile(r'def build_features.*?return np\.array\(\[.*?\]\)', re.DOTALL)
content = build_features_regex.sub('', content)

# 7. Update assess_student
assess_sig_old = """@app.post("/v1/assess", response_model=AssessmentResponse)
async def assess_student(profile: StudentProfile, background_tasks: BackgroundTasks, request: Request, tenant: dict = Depends(get_current_tenant)):"""

assess_sig_new = """def _get_tenant_rate_limit(request: Request) -> int:
    tenant = getattr(request.state, "tenant", None)
    if tenant and tenant.get("rate_limit_rpm"):
        return tenant["rate_limit_rpm"]
    return int(EnvConfig.optional("RATE_LIMIT_DEFAULT_RPM", "100", "default rpm"))

@app.post("/v1/assess", response_model=AssessmentResponse)
@limiter.limit(lambda request: f"{_get_tenant_rate_limit(request)}/minute")
async def assess_student(profile: AssessRequest, background_tasks: BackgroundTasks, request: Request, tenant: dict = Depends(get_current_tenant)):"""
content = content.replace(assess_sig_old, assess_sig_new)

# 8. Rate limit & consent check in assess_student
consent_check_old = """    # 0. Rate Limit & Consent Check
    await check_rate_limit(tenant["tenant_id"], tenant["rate_limit_rpm"], request)
    if profile.user_hash:
        if not await check_consent(request.app.state.db_pool, profile.user_hash):
            raise HTTPException(status_code=403, detail="DPDP Consent missing or withdrawn")"""

consent_check_new = """    # 0. Consent Check (Rate limit handled by decorator)
    if not profile.has_consent:
        raise HTTPException(status_code=422, detail="Explicit consent is required")"""
content = content.replace(consent_check_old, consent_check_new)

# 9. Transform features replacement
transform_old = """    features = build_features(profile, demand_lookup, velocity_lookup, market_hhi, macro_index)"""

transform_new = """    temporal = TemporalFeatures(
        velocity=velocity_lookup.get(profile.field_of_study, {}).get("velocity", 0.0),
        accel=velocity_lookup.get(profile.field_of_study, {}).get("accel", 0.0),
        r2=velocity_lookup.get(profile.field_of_study, {}).get("r2", 0.0)
    )
    market = MarketFeatures(
        demand_proxy=demand_lookup.get(profile.field_of_study, 0.5),
        market_hhi=market_hhi,
        macro_index=macro_index
    )
    features = FeaturePipeline.transform(
        cgpa=profile.cgpa,
        internships_count=profile.internships_count,
        backlogs=profile.backlogs,
        field_of_study=profile.field_of_study,
        college_placement_rate=profile.college_placement_rate,
        salary_norm=get_nirf_salary_norm(profile.field_of_study),
        temporal=temporal,
        market=market,
        backlogs_missing=0
    )"""

content = content.replace(transform_old, transform_new)

# 10. Atomic transaction
atomic_old = """    # 5. Monitoring & Logging
    assessment_id = str(uuid.uuid4())
    PREDICTION_COUNTER.labels(risk_tier, profile.field_of_study, tenant["tenant_id"]).inc()
    PREDICTION_PROBABILITY.observe(cal_prob)
    background_tasks.add_task(log_api_call, app.state.db_pool, assessment_id, json.dumps(dict(zip(feature_names, features.tolist()))), cal_prob, risk_tier, tenant["tenant_id"])"""

atomic_new = """    # 5. Monitoring & Logging
    assessment_id = str(uuid.uuid4())
    from app.api.consent import record_consent
    
    async with request.app.state.db_pool.acquire() as conn:
        async with conn.transaction():
            consent_id = await record_consent(
                conn,
                profile.user_hash,
                profile.has_consent,
                request.client.host,
                request.headers.get("user-agent", ""),
                profile.consent.data_sources
            )
            features_json = json.dumps(dict(zip(feature_names, features.tolist())))
            await conn.execute(\"""
                INSERT INTO assessments (id, profile_data, calibrated_probability, risk_tier, shap_values)
                VALUES ($1, $2, $3, $4, $5)
            \""", uuid.UUID(assessment_id), profile.model_dump_json(), cal_prob, risk_tier, json.dumps(shap_contributions))
            await conn.execute(\"""
                INSERT INTO api_calls (assessment_id, features_json, prediction, risk_tier, api_key_id)
                VALUES ($1, $2, $3, $4, $5)
            \""", uuid.UUID(assessment_id), features_json, cal_prob, risk_tier, tenant["tenant_id"])

    PREDICTION_COUNTER.labels(risk_tier, profile.field_of_study, tenant["tenant_id"]).inc()
    PREDICTION_PROBABILITY.observe(cal_prob)"""
content = content.replace(atomic_old, atomic_new)

with open("app/api/main.py", "w") as f:
    f.write(content)

