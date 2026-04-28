import asyncio
import asyncpg
import secrets
import sys
import os

# Add project root to path for imports
sys.path.append(os.getcwd())

from app.api.auth import hash_api_key
from config import EnvConfig

async def seed():
    print("EduPredict AI — Demo Key Seeding Script")
    print("========================================")
    
    db_url = EnvConfig.DATABASE_URL()
    try:
        pool = await asyncpg.create_pool(db_url)
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return
    
    # We use a stable demo key for the integrated dashboard/frontend
    demo_key = "ep_demo_dashboard_key_2026"
    key_hash = hash_api_key(demo_key)
    
    async with pool.acquire() as conn:
        # Ensure table exists (though migration should handle this)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS api_keys (
                id SERIAL PRIMARY KEY,
                tenant_id VARCHAR(50) UNIQUE NOT NULL,
                key_hash TEXT UNIQUE NOT NULL,
                rate_limit_rpm INTEGER DEFAULT 60,
                active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await conn.execute("""
            INSERT INTO api_keys (tenant_id, key_hash, rate_limit_rpm, active)
            VALUES ('demo_lender', $1, 1000, TRUE)
            ON CONFLICT (tenant_id) DO UPDATE 
            SET key_hash = EXCLUDED.key_hash, active = TRUE
        """, key_hash)
    
    print(f"✅ Demo key seeded for tenant 'demo_lender'")
    print(f"   Key: {demo_key}")
    print("   Store this key securely. It is required for dashboard access.")
    
    await pool.close()

if __name__ == "__main__":
    asyncio.run(seed())
