import asyncio
import asyncpg
import secrets
import sys
import os
import argparse

# Add project root to path for imports
sys.path.append(os.getcwd())

from app.api.auth import hash_api_key
from config import EnvConfig

async def seed():
    print("EduPredict AI — Demo Key Seeding Script")
    print("========================================")
    
    parser = argparse.ArgumentParser(description="Seed demo API key")
    parser.add_argument("--key", type=str, help="Demo API key to seed")
    args = parser.parse_args()

    demo_key = args.key or os.environ.get("SEED_DEMO_KEY")
    if not demo_key:
        demo_key = "ep_" + secrets.token_urlsafe(32)

    key_hash = hash_api_key(demo_key)

    db_url = EnvConfig.DATABASE_URL()
    try:
        pool = await asyncpg.create_pool(db_url)
    except Exception as e:
        print(f"❌ Failed to connect to database: {e}")
        return

    async with pool.acquire() as conn:
        await conn.execute("DELETE FROM api_keys WHERE tenant_id = 'demo_lender'")
        await conn.execute("""
            INSERT INTO api_keys (tenant_id, key_hash, rate_limit_rpm, active)
            VALUES ('demo_lender', $1, 1000, TRUE)
        """, key_hash)

    print(f"✅ Demo key seeded for tenant 'demo_lender'")
    print(f"   Plaintext key: {demo_key}")
    print("   Store this securely. It will not be shown again.")

    await pool.close()

if __name__ == "__main__":
    asyncio.run(seed())
