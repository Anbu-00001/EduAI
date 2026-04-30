"""
Digital Personal Data Protection (DPDP) Act 2023 Compliance Layer

Under Section 6 of DPDP Act 2023, every data principal (student) must:
  1. Give explicit, informed consent BEFORE their data is processed
  2. Be able to withdraw consent at any time
  3. Know which data sources are being accessed
  4. Receive a notice in plain language

For EduPredict AI, data sources accessed:
  - Academic records (CGPA, backlogs): provided by user
  - Employment market data (Naukri, LinkedIn, Indeed): scraped public data
  - Government employment data (data.gov.in): public API
  - Peer cohort similarity: derived from anonymised training set

Consent is stored in PostgreSQL with timestamp and version.
If consent is revoked, all stored assessments for that user
are queued for deletion within 72 hours (DPDP requirement).
"""

import hashlib
import time
import json
import logging
import os
from typing import Optional
import asyncpg
from fastapi import HTTPException

logger = logging.getLogger(__name__)

CONSENT_NOTICE_VERSION = "1.0"

CONSENT_NOTICE_TEXT = {
    "version": CONSENT_NOTICE_VERSION,
    "data_sources": [
        {
            "name": "Academic records",
            "type": "User-provided",
            "purpose": "Compute CGPA-based repayment potential score",
            "retention_days": 365,
        },
        {
            "name": "Job market data",
            "type": "Public web scraping (Naukri, LinkedIn, Indeed)",
            "purpose": "Assess demand for your field of study",
            "retention_days": 30,
        },
        {
            "name": "Government employment statistics",
            "type": "data.gov.in public API",
            "purpose": "Cross-reference sector employment rates",
            "retention_days": 90,
        },
        {
            "name": "Peer cohort analysis",
            "type": "Anonymised aggregation of similar profiles",
            "purpose": "Graph-regularised probability estimate",
            "retention_days": 0,  # Not stored individually
        },
    ],
    "rights": [
        "Access your assessment history",
        "Withdraw consent and delete your data",
        "Receive explanation for any adverse decision (adverse action code)",
        "Lodge grievance with data protection officer",
    ],
    "dpo_contact": os.environ.get("DPO_EMAIL", "dpo@edupredict.ai"),
}


async def record_consent(
    conn_or_pool: asyncpg.Connection | asyncpg.Pool,
    user_hash: str,           # SHA-256 of (phone_number + salt) — never store raw PII
    consent_given: bool,
    ip_address: str,
    user_agent: str,
    data_sources: list[str],
) -> str:
    """
    Store consent record. Returns consent_id.
    user_hash must be computed by caller — API never sees raw PII.
    """
    consent_id = hashlib.sha256(
        f"{user_hash}{time.time()}".encode()
    ).hexdigest()[:32]

    query = """
        INSERT INTO consent_records 
        (consent_id, user_hash, consent_given, notice_version,
         data_sources, ip_hash, user_agent_hash, created_at)
        VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
    """
    params = (
        consent_id,
        user_hash,
        consent_given,
        CONSENT_NOTICE_VERSION,
        json.dumps(data_sources),
        hashlib.sha256(ip_address.encode()).hexdigest()[:16],
        hashlib.sha256(user_agent.encode()).hexdigest()[:16],
    )

    if isinstance(conn_or_pool, asyncpg.Connection):
        await conn_or_pool.execute(query, *params)
    else:
        async with conn_or_pool.acquire() as conn:
            await conn.execute(query, *params)
            
    return consent_id


async def check_consent(db_pool, user_hash: str) -> bool:
    """
    Returns True if user has active (not withdrawn) consent.
    """
    async with db_pool.acquire() as conn:
        row = await conn.fetchrow("""
            SELECT consent_given FROM consent_records
            WHERE user_hash = $1
            ORDER BY created_at DESC LIMIT 1
        """, user_hash)
    return bool(row and row["consent_given"])


def get_consent_notice() -> dict:
    """Return the current consent notice (shown to user before assessment)."""
    return CONSENT_NOTICE_TEXT
