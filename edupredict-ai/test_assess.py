import asyncio, httpx, json, uuid
async def test():
    async with httpx.AsyncClient() as client:
        payload = {
            "cgpa": 8.5,
            "internships_count": 1,
            "backlogs": 0,
            "field_of_study": "computer_science",
            "college_placement_rate": 80.0,
            "loan_amount_inr": 500000.0,
            "annual_family_income_inr": 600000.0,
            "user_hash": str(uuid.uuid4()),
            "has_consent": True,
            "consent": {
                "data_sources": ["Academic Records", "Job Market Data"],
                "notice_version": "1.0"
            }
        }
        res = await client.post("http://localhost:8000/v1/assess", json=payload, headers={"X-API-Key": "ep_demo_lender_2026"})
        if res.status_code != 200:
            print(f"Failed with {res.status_code}")
            print(res.text)
        else:
            print("Success!")
            print(res.json())

asyncio.run(test())
