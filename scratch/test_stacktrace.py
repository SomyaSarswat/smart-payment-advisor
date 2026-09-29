import sys
import os
import asyncio
import traceback
from fastapi import HTTPException

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from main import (
    simulate_failure_endpoint, SimulateFailureRequest,
    recommendations_endpoint, RecommendationRequest,
    merchant_config_endpoint,
    analytics_endpoint
)

print("--- Testing /api/merchant-config/Electricity Bill Portal ---")
try:
    res = merchant_config_endpoint("Electricity Bill Portal")
    print("Config Response:", res)
except Exception:
    traceback.print_exc()

print("\n--- Testing /api/get-recommendations with Electricity Bill Portal ---")
try:
    req = RecommendationRequest(merchant_id="Electricity Bill Portal", amount=500.0)
    res = recommendations_endpoint(req)
    print("Recommendations Response:", res)
except Exception:
    traceback.print_exc()

print("\n--- Testing /api/analytics/Electricity Bill Portal ---")
try:
    res = analytics_endpoint("Electricity Bill Portal")
    print("Analytics Response:", res)
except Exception:
    traceback.print_exc()

print("\n--- Testing /api/simulate-failure with Electricity Bill Portal ---")
try:
    req = SimulateFailureRequest(merchant_id="Electricity Bill Portal", method="Net Banking", bank="HDFC")
    res = simulate_failure_endpoint(req)
    print("Simulate Failure Response:", res)
except Exception:
    traceback.print_exc()
