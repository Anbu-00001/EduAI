import argparse
import asyncio
import httpx
import numpy as np
from datetime import datetime, timedelta
import uuid
import random

FIELDS = [
    'computer_science', 'data_science', 'mba_finance', 
    'mechanical_engineering', 'electrical_engineering', 
    'civil_engineering', 'biotechnology'
]

async def seed_data(count, days, tenant_id, api_key):
    print(f"→ Seeding {count} assessments across {days} days for tenant {tenant_id}")
    
    # Generate distribution of days
    # Poisson-ish distribution across days
    days_ago = np.random.poisson(lam=days/2, size=count)
    days_ago = np.clip(days_ago, 0, days)
    
    async with httpx.AsyncClient(base_url="http://localhost:8000", headers={"X-API-Key": api_key}, timeout=15.0) as client:
        latencies = []
        outcomes = {"GREEN": 0, "AMBER": 0, "RED": 0}
        
        # We need to simulate the passage of time.
        # But wait, the API uses `time.time()` for its timestamps and DB inserts use `NOW()`.
        # We can't change the DB timestamp via the API.
        # Wait, the prompt says "run_demo.sh ... seeds 50 assessments across 7 days".
        # If I just call `/v1/assess`, the `created_at` will all be NOW().
        # Is there a way to override timestamp, or should I just insert directly into DB?
        # Prompt: "Calls the actual /v1/assess endpoint locally — does NOT bypass the model. This guarantees realistic distributions and ensures Prometheus metrics get populated."
        # Ah! But if I just call the API, how do I get them "distributed across the last N days"?
        # I'll call the API, let it insert with NOW(), and then run an UPDATE query to backdate them!
        
        assessment_ids = []
        
        for i in range(count):
            cgpa = float(np.clip(np.random.normal(7.5, 1.0), 4.0, 10.0))
            field = random.choice(FIELDS)
            internships = random.randint(0, 4)
            backlogs = 0 if random.random() < 0.8 else random.randint(1, 3)
            placement = float(np.clip(np.random.normal(70, 15), 30, 100))
            loan = random.choice([200000, 350000, 500000, 750000, 1000000, 1500000])
            
            payload = {
                "cgpa": round(cgpa, 2),
                "internships_count": internships,
                "backlogs": backlogs,
                "field_of_study": field,
                "college_placement_rate": round(placement, 2),
                "loan_amount_inr": loan,
                "annual_family_income_inr": None,
                "user_hash": str(uuid.uuid4()),
                "has_consent": True,
                "cgpa_verified": random.random() > 0.5,
                "institution_verified": random.random() > 0.3,
                "consent": {
                    "data_sources": ["Academic Records", "Job Market Data"],
                    "notice_version": "1.0"
                }
            }
            
            t0 = datetime.now()
            res = await client.post("/v1/assess", json=payload)
            t1 = datetime.now()
            lat_ms = (t1 - t0).total_seconds() * 1000
            latencies.append(lat_ms)
            
            if res.status_code == 200:
                data = res.json()
                outcomes[data["risk_tier"]] += 1
                assessment_ids.append((data["assessment_id"], days_ago[i]))
            else:
                print("Error:", res.text)
                
        # Now backdate the assessments in the database
        import asyncpg
        try:
            from config import EnvConfig
            conn = await asyncpg.connect(EnvConfig.DATABASE_URL())
            for a_id, d_ago in assessment_ids:
                if d_ago > 0:
                    delta = timedelta(days=float(d_ago), hours=random.randint(0, 23), minutes=random.randint(0, 59))
                    new_time = datetime.now() - delta
                    await conn.execute("UPDATE assessments SET created_at = $1 WHERE id = $2", new_time, uuid.UUID(a_id))
                    await conn.execute("UPDATE api_calls SET timestamp = $1 WHERE assessment_id = $2", new_time, uuid.UUID(a_id))
            await conn.close()
        except Exception as e:
            print("Could not backdate in DB:", e)
            
        print(f"Seeded {count} assessments across {days} days")
        print(f"GREEN: {outcomes['GREEN']} ({int(outcomes['GREEN']/count*100)}%) · AMBER: {outcomes['AMBER']} ({int(outcomes['AMBER']/count*100)}%) · RED: {outcomes['RED']} ({int(outcomes['RED']/count*100)}%)")
        print(f"Avg latency: {int(np.mean(latencies))}ms · Avg P99: {int(np.percentile(latencies, 99))}ms")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=50)
    parser.add_argument("--days", type=int, default=7)
    parser.add_argument("--tenant_id", type=str, default="demo_lender")
    parser.add_argument("--api_key", type=str, required=True)
    args = parser.parse_args()
    
    asyncio.run(seed_data(args.count, args.days, args.tenant_id, args.api_key))
