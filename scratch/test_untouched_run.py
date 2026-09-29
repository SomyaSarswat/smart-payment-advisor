import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from data_simulator import generate_one_fake_transaction, simulator
from database import init_db

def run_untouched_observation(duration_seconds=180):
    print("="*75)
    print(f"STARTING UNTOUCHED AUTONOMOUS ECOSYSTEM RUN FOR {duration_seconds} SECONDS")
    print("NO MANUAL INCIDENT TRIGGERS - PURE ORGANIC SIMULATION")
    print("="*75)
    
    init_db()
    start_time = time.time()
    tx_count = 0
    incidents_seen = []
    
    while time.time() - start_time < duration_seconds:
        tx = generate_one_fake_transaction()
        tx_count += 1
        elapsed = int(time.time() - start_time)
        
        # Check if any incident factor is logged
        for factor in tx['audit_factors']:
            if "ACTIVE INCIDENT" in factor or "INCIDENT RECOVERING" in factor:
                if factor not in incidents_seen:
                    incidents_seen.append(factor)
                    print(f"\n>>> [NATURAL AUTONOMY CONFIRMED at t={elapsed}s]: {factor} <<<\n")
        
        # Sleep for dynamic generation interval
        interval = simulator.get_current_generation_interval()
        time.sleep(interval)
        
    print("\n" + "="*75)
    print(f"UNTOUCHED RUN COMPLETED IN {int(time.time() - start_time)}s")
    print(f"Total Transactions Generated: {tx_count}")
    print(f"Autonomous Incident Factors Detected: {len(incidents_seen)}")
    for inc in incidents_seen:
        print(f"  - {inc}")
    print("="*75)

if __name__ == "__main__":
    run_untouched_observation(180) # 3 minutes run
