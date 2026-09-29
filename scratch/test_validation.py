import sys
import os
import asyncio
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from main import (
    simulate_failure_endpoint, SimulateFailureRequest
)

async def run_tests():
    print("=== TEST 1: Unknown merchant ===")
    try:
        req = SimulateFailureRequest(merchant_id="random_invalid_merchant", method="Net Banking", bank="HDFC")
        res = simulate_failure_endpoint(req)
        print("FAIL: Expected 400, got success:", res)
    except HTTPException as e:
        print(f"SUCCESS: Caught HTTPException {e.status_code}: {e.detail}")

    print("\n=== TEST 2: 'Electricity Bill Portal' (UI display label) ===")
    try:
        req = SimulateFailureRequest(merchant_id="Electricity Bill Portal", method="Net Banking", bank="HDFC", failure_count=10)
        res = simulate_failure_endpoint(req)
        print("SUCCESS:", res['message'], "| Normalized ID:", res['details']['merchant_id'])
    except Exception as e:
        print("FAIL:", e)

    print("\n=== TEST 3: 'electricity_bill' (internal ID) ===")
    try:
        req = SimulateFailureRequest(merchant_id="electricity_bill", method="Net Banking", bank="HDFC", failure_count=10)
        res = simulate_failure_endpoint(req)
        print("SUCCESS:", res['message'], "| Normalized ID:", res['details']['merchant_id'])
    except Exception as e:
        print("FAIL:", e)

    print("\n=== TEST 4: 'college_fee_portal' (internal ID) ===")
    try:
        req = SimulateFailureRequest(merchant_id="college_fee_portal", method="Credit Card", bank="SBI", failure_count=10)
        res = simulate_failure_endpoint(req)
        print("SUCCESS:", res['message'], "| Normalized ID:", res['details']['merchant_id'])
    except Exception as e:
        print("FAIL:", e)

    print("\n=== TEST 5: 'ecommerce_store' (internal ID) ===")
    try:
        req = SimulateFailureRequest(merchant_id="ecommerce_store", method="UPI", bank=None, failure_count=10)
        res = simulate_failure_endpoint(req)
        print("SUCCESS:", res['message'], "| Normalized ID:", res['details']['merchant_id'])
    except Exception as e:
        print("FAIL:", e)

if __name__ == "__main__":
    asyncio.run(run_tests())
