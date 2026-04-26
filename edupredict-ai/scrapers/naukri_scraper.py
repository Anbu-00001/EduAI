import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os

DEGREE_FIELDS = [
    "computer-science", "mechanical-engineering", 
    "mba-finance", "data-science", "civil-engineering",
    "electrical-engineering", "biotechnology"
]

def scrape_job_count(field: str) -> dict:
    """Scrape job count for a degree field from Naukri."""
    try:
        url = f"https://www.naukri.com/{field}-jobs"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        
        # Try multiple selectors — Naukri changes their DOM frequently
        count_selectors = [
            ("span", {"class": "count"}),
            ("span", {"class": "jobCount"}),
            ("span", {"class": "ni-job-count"}),
        ]
        count = 0
        for tag, attrs in count_selectors:
            el = soup.find(tag, attrs)
            if el:
                text = el.get_text().replace(",", "").strip()
                digits = ''.join(filter(str.isdigit, text))
                if digits:
                    count = int(digits)
                    break
        
        return {
            "field": field, 
            "job_count": count if count > 0 else None,
            "scraped": count > 0
        }
    except Exception as e:
        return {"field": field, "job_count": None, "scraped": False, "error": str(e)}

def build_demand_table() -> pd.DataFrame:
    records = []
    any_scraped = False
    for field in DEGREE_FIELDS:
        result = scrape_job_count(field)
        records.append(result)
        print(f"  {field}: {result.get('job_count', 'failed')}")
        if result.get('scraped'): any_scraped = True
        time.sleep(1.0) # Reduced sleep for faster execution
    
    df = pd.DataFrame(records)
    
    if not any_scraped:
        print("Scraping failed for all fields. Using fallback data.")
        fallback = {
            "computer-science": 285000,
            "data-science": 142000,
            "mba-finance": 98000,
            "mechanical-engineering": 76000,
            "electrical-engineering": 68000,
            "civil-engineering": 45000,
            "biotechnology": 28000
        }
        df["job_count"] = df["field"].map(fallback)
        df["scraped"] = False

    # Fill nulls with field median
    median_count = df["job_count"].median()
    df["job_count"] = df["job_count"].fillna(median_count)
    df["job_count_normalized"] = df["job_count"] / df["job_count"].max()
    return df

if __name__ == "__main__":
    print("Scraping Naukri job counts...")
    df = build_demand_table()
    os.makedirs("edupredict-ai/data/raw", exist_ok=True)
    df.to_csv("edupredict-ai/data/raw/naukri_jobs.csv", index=False)
    print(df)
