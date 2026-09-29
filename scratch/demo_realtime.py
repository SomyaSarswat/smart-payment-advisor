import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from data_simulator import generate_one_fake_transaction
from recommendation_engine import get_recommendations
from database import inject_failure_spike

merchant = "college_fee_portal"
methods = [("Net Banking", "HDFC"), ("UPI", None), ("Credit Card", "SBI")]

print("=== LIVE REAL-TIME RE-RANKING DEMONSTRATION ===")

print("\n--- MOMENT 1: Initial Fetch ---")
recs_1 = get_recommendations(merchant, 5000.0, "Android", methods)
for r in recs_1:
    print(f"[{r['computed_at']}] {r['method']}{' ('+r['bank']+')' if r['bank'] else ''}: {r['success_rate']}% +/- {r['confidence_interval']}% | {r['reason']}")

print("\n... Simulating background transaction worker running for 5 seconds ...")
for _ in range(5):
    generate_one_fake_transaction()
    time.sleep(1)

print("\n--- MOMENT 2: Fetch After Background Worker Activity ---")
recs_2 = get_recommendations(merchant, 5000.0, "Android", methods)
for r in recs_2:
    print(f"[{r['computed_at']}] {r['method']}{' ('+r['bank']+')' if r['bank'] else ''}: {r['success_rate']}% +/- {r['confidence_interval']}% | {r['reason']}")

print("\n--- TRIGGERING FAILURE SPIKE FOR Net Banking (HDFC) VIA SIMULATOR ---")
result = inject_failure_spike(merchant_id=merchant, method="Net Banking", bank="HDFC", failure_count=15)
print(f"Injected {result['injected_count']} failures into database.")

print("\n--- MOMENT 3: Immediate Fetch Seconds After Failure Spike ---")
recs_3 = get_recommendations(merchant, 5000.0, "Android", methods)
for r in recs_3:
    print(f"[{r['computed_at']}] {r['method']}{' ('+r['bank']+')' if r['bank'] else ''}: {r['success_rate']}% +/- {r['confidence_interval']}% | {r['reason']}")
