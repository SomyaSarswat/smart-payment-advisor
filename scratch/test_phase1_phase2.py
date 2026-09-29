import sys
import os
import asyncio
from fastapi import HTTPException
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from main import app, rate_limit_store
from database import DatabaseUnavailableError

client = TestClient(app)

print("=== VERIFICATION 1: Invalid merchant_id (404/400) ===")
res = client.get("/api/merchant-config/unknown_merchant_999")
print("Status:", res.status_code, "| Response:", res.json())
assert res.status_code in [400, 404]

print("\n=== VERIFICATION 2: Invalid Amount (-500) (422/400) ===")
res = client.post("/api/get-recommendations", json={
    "merchant_id": "college_fee_portal",
    "amount": -500
})
print("Status:", res.status_code, "| Response:", res.json())
assert res.status_code in [400, 422]

print("\n=== VERIFICATION 3: Rate Limiting (11th+ Request -> 429) ===")
rate_limit_store.clear()
statuses = []
for i in range(12):
    r = client.post("/api/simulate-failure", json={
        "merchant_id": "college_fee_portal",
        "method": "Net Banking",
        "bank": "HDFC",
        "failure_count": 5
    })
    statuses.append(r.status_code)
print("Request statuses (1-12):", statuses)
assert 429 in statuses

print("\n=== VERIFICATION 4: Database Unavailable Error Handler (503) ===")
from database import get_merchant_analytics, DatabaseUnavailableError
import database
original_get = database.get_connection
def mock_locked_connection():
    raise DatabaseUnavailableError("Database is locked by another process")
database.get_connection = mock_locked_connection

res = client.get("/api/analytics/college_fee_portal")
print("Status when DB locked:", res.status_code, "| Response:", res.json())
assert res.status_code == 503
database.get_connection = original_get

print("\n=== VERIFICATION 5: Confirm .env is NOT served statically ===")
res = client.get("/.env")
print("GET /.env status:", res.status_code)
assert res.status_code in [404, 405]

print("\n>>> ALL PHASE 1 & PHASE 2 VERIFICATIONS PASSED SUCCESSFULLY! <<<")
