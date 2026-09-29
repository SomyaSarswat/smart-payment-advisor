import sys
import os
import asyncio
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from database import get_windowed_stats_sql, get_windowed_transactions_decay, insert_transaction
from recommendation_engine import (
    get_recommendations,
    calculate_exponential_decay_rate,
    calculate_confidence_interval,
    generate_reason,
    DECAY_CONSTANT
)

print("=== UPGRADE 1: Database-Level Windowed Aggregation ===")
stats = get_windowed_stats_sql(merchant_id="college_fee_portal", method="Net Banking", bank="HDFC", hours_lookback=2)
print("SQL Aggregation Result:", stats)

print("\n=== UPGRADE 2: Exponential Decay Recency Weighting ===")
print(f"Decay constant: {DECAY_CONSTANT}")
w_5m = math_exp = math_exp_val = 1.0
import math
w_5m = math.exp(-DECAY_CONSTANT * 5)
w_30m = math.exp(-DECAY_CONSTANT * 30)
print(f"Weight at 5 min: {round(w_5m, 4)} | Weight at 30 min: {round(w_30m, 4)} | Ratio: {round(w_5m / w_30m, 2)}x")

print("\n=== UPGRADE 3: Statistical Anomaly Detection ===")
reason_normal = generate_reason("Net Banking", "HDFC", current_rate=92.0, baseline_rate=95.0, confidence_level="high", data_points=20)
print("Normal Reason:", reason_normal)
reason_anomaly = generate_reason("Net Banking", "HDFC", current_rate=45.0, baseline_rate=95.0, confidence_level="high", data_points=20)
print("Anomaly Reason:", reason_anomaly)

print("\n=== UPGRADE 4: Visible Freshness & Confidence Metadata ===")
recs = get_recommendations("college_fee_portal", 5000.0, "Android", [("Net Banking", "HDFC"), ("UPI", None)])
for r in recs:
    bank_str = f" ({r['bank']})" if r['bank'] else ""
    print(f"Method: {r['method']}{bank_str}")
    print(f"  Success Rate: {r['success_rate']}% ± {r['confidence_interval']}%")
    print(f"  Reason: {r['reason']}")
    print(f"  Computed At: {r['computed_at']}")
