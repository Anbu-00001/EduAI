import re

with open("app/api/auth.py", "r") as f:
    content = f.read()

content = content.replace("import secrets", "import secrets\nimport json")

content = content.replace("JWT_ALGORITHM = \"HS256\"", "VALID_PERMISSIONS = {\"assess\", \"admin\", \"data_refresh\"}\n\nJWT_ALGORITHM = \"HS256\"")

old_query = '''        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT tenant_id, rate_limit_rpm, active "
                "FROM api_keys WHERE key_hash = $1",
                key_hash
            )
        if not row or not row["active"]:
            raise HTTPException(status_code=401, detail="Invalid API key")
        return {
            "tenant_id": row["tenant_id"],
            "rate_limit_rpm": row["rate_limit_rpm"],
            "auth_method": "api_key",
        }'''

new_query = '''        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT tenant_id, rate_limit_rpm, permissions, active "
                "FROM api_keys WHERE key_hash = $1",
                key_hash
            )
        if not row or not row["active"]:
            raise HTTPException(status_code=401, detail="Invalid API key")
            
        perms = json.loads(row["permissions"]) if isinstance(row["permissions"], str) else row["permissions"]
        
        return {
            "tenant_id": row["tenant_id"],
            "rate_limit_rpm": row["rate_limit_rpm"],
            "permissions": perms,
            "auth_method": "api_key",
        }'''
content = content.replace(old_query, new_query)

old_jwt = '''        return {
            "tenant_id": payload["sub"],
            "rate_limit_rpm": EnvConfig.RATE_LIMIT_DEFAULT_RPM(),
            "auth_method": "jwt",
        }'''

new_jwt = '''        return {
            "tenant_id": payload["sub"],
            "rate_limit_rpm": int(EnvConfig.optional("RATE_LIMIT_DEFAULT_RPM", "100", "default rpm")),
            "permissions": ["admin"] if payload["sub"] == "admin" else ["assess"],
            "auth_method": "jwt",
        }'''
content = content.replace(old_jwt, new_jwt)

with open("app/api/auth.py", "w") as f:
    f.write(content)

