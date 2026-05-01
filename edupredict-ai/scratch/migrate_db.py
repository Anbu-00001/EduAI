import asyncio
import asyncpg
from config import EnvConfig

async def migrate():
    conn = await asyncpg.connect(EnvConfig.DATABASE_URL())
    print("Migrating column lengths...")
    await conn.execute("ALTER TABLE api_calls ALTER COLUMN api_key_id TYPE VARCHAR(128)")
    await conn.execute("ALTER TABLE api_keys ALTER COLUMN tenant_id TYPE VARCHAR(128)")
    print("✅ Migration complete.")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate())
