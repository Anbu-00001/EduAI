import re

# Update main.py
with open("app/api/main.py", "r") as f:
    main_py = f.read()

student_session_endpoint = """
class StudentSessionRequest(BaseModel):
    user_hash: str

@app.post("/v1/auth/student-session")
@limiter.limit("10/minute")
async def create_student_session(req: StudentSessionRequest, request: Request):
    from app.api.auth import create_student_jwt_token
    token, expires_in = create_student_jwt_token(req.user_hash)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": expires_in
    }

class ConsentBlock(BaseModel):"""

main_py = main_py.replace("class ConsentBlock(BaseModel):", student_session_endpoint)

with open("app/api/main.py", "w") as f:
    f.write(main_py)

# Update auth.py
with open("app/api/auth.py", "r") as f:
    auth_py = f.read()

# Add create_student_jwt_token
create_jwt_code = """
def create_student_jwt_token(user_hash: str) -> tuple[str, int]:
    expires_in_seconds = 4 * 3600
    payload = {
        "sub": user_hash,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=4),
        "type": "student",
    }
    return jwt.encode(payload, EnvConfig.JWT_SECRET(), algorithm=JWT_ALGORITHM), expires_in_seconds

def create_jwt_token(tenant_id: str) -> str:"""
auth_py = auth_py.replace("def create_jwt_token(tenant_id: str) -> str:", create_jwt_code)

# Update get_current_tenant
old_jwt_check = """    if credentials:
        payload = verify_jwt_token(credentials.credentials)
        return {
            "tenant_id": payload["sub"],
            "rate_limit_rpm": int(EnvConfig.optional("RATE_LIMIT_DEFAULT_RPM", "100", "default rpm")),
            "permissions": ["admin"] if payload["sub"] == "admin" else ["assess"],
            "auth_method": "jwt",
        }"""

new_jwt_check = """    if credentials:
        payload = verify_jwt_token(credentials.credentials)
        if payload.get("type") == "student":
            return {
                "tenant_id": payload["sub"],
                "role": "student",
                "rate_limit_rpm": 20,
                "permissions": ["assess"],
                "auth_method": "jwt",
            }
        else:
            return {
                "tenant_id": payload["sub"],
                "rate_limit_rpm": int(EnvConfig.optional("RATE_LIMIT_DEFAULT_RPM", "100", "default rpm")),
                "permissions": ["admin"] if payload["sub"] == "admin" else ["assess"],
                "auth_method": "jwt",
            }"""
auth_py = auth_py.replace(old_jwt_check, new_jwt_check)

with open("app/api/auth.py", "w") as f:
    f.write(auth_py)

