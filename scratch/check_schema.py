import asyncio
import asyncpg
import os
from config import EnvConfig

async def check_schema():
    conn = await asyncpg.connect(EnvConfig.DATABASE_URL())
    tables = ['assessments', 'api_calls', 'api_keys']
    for table in tables:
        print(f"\nTable: {table}")
        columns = await conn.fetch(f"""
            SELECT column_name, data_type, character_maximum_length 
            FROM information_schema.columns 
            WHERE table_name = '{table}'
            ORDER BY ordinal_position
        """)
        for col in columns:
            print(f"  {col['column_name']}: {col['data_type']} ({col['character_maximum_length']})")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(check_schema())
