import sys
import os
import time
from datetime import datetime

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from data_simulator import (
    EcosystemSimulator, simulator, generate_one_fake_transaction,
    trigger_incident, get_current_generation_interval
)
from database import inject_failure_spike, init_db

def test_upgrades():
    print("="*70)
    print("RUNNING MULTI-FACTOR PAYMENT ECOSYSTEM VERIFICATION SUITE")
    print("="*70)
    
    init_db()

    # 1. VERIFY UPGRADE 3: Hard Amount Limits (UPI > 1Lakh & Wallet > 20k)
    print("\n--- [VERIFICATION B] Payment Method Real Limits ---")
    upi_tx = generate_one_fake_transaction(method="UPI", amount=125000.0)
    print(f"UPI > 1 Lakh Result: Status={upi_tx['status']}, Error={upi_tx['error_code']}, Prob={upi_tx['calculated_probability']}")
    print(f"Factors: {upi_tx['audit_factors']}")
    assert upi_tx['status'] == 'failed'
    assert upi_tx['error_code'] == 'amount_limit_exceeded'
    
    wallet_tx = generate_one_fake_transaction(method="Wallet", amount=25000.0)
    print(f"Wallet > 20k Result: Status={wallet_tx['status']}, Error={wallet_tx['error_code']}, Prob={wallet_tx['calculated_probability']}")
    print(f"Factors: {wallet_tx['audit_factors']}")
    assert wallet_tx['status'] == 'failed'
    assert wallet_tx['error_code'] == 'amount_limit_exceeded'

    card_tx = generate_one_fake_transaction(method="Credit Card", bank="HDFC", amount=75000.0, hour=14)
    print(f"Card > 50k Fraud Check Result: Status={card_tx['status']}, Prob={card_tx['calculated_probability']}")
    print(f"Factors: {card_tx['audit_factors']}")
    assert any("fraud check risk" in f for f in card_tx['audit_factors'])

    # 2. VERIFY UPGRADE 1 & 4: Time of Day & Generation Rate differences
    print("\n--- [VERIFICATION C] Peak vs Off-Peak Rush & Load Differences ---")
    peak_info = simulator.get_hourly_rush_info(hour=10) # 10 AM peak
    offpeak_info = simulator.get_hourly_rush_info(hour=3) # 3 AM off-peak
    
    print(f"Peak Hour (10:00 AM): Multiplier={peak_info['multiplier']}x, Load Penalty={peak_info['load_penalty']*100}%, Interval={peak_info['interval_range']}s")
    print(f"Off-Peak Hour (03:00 AM): Multiplier={offpeak_info['multiplier']}x, Load Penalty={offpeak_info['load_penalty']*100}%, Interval={offpeak_info['interval_range']}s")
    
    # Calculate simulated generation rate (transactions per minute)
    peak_avg_interval = sum(peak_info['interval_range']) / 2.0
    offpeak_avg_interval = sum(offpeak_info['interval_range']) / 2.0
    print(f"Simulated Peak Generation Rate: ~{60/peak_avg_interval:.1f} tx/min")
    print(f"Simulated Off-Peak Generation Rate: ~{60/offpeak_avg_interval:.1f} tx/min")

    # 3. VERIFY UPGRADE 2: Autonomous Incident Scheduler & Smooth Recovery
    print("\n--- [VERIFICATION A] Autonomous Incident Trigger & Recovery Window ---")
    # Trigger a 12-second compressed incident on ICICI Net Banking for test observation
    simulator.trigger_incident("ICICI", "Net Banking", duration_seconds=12, drop_depth=0.25)
    
    print("\nPhase A1: During Incident Peak (t=2s)")
    time.sleep(2)
    inc_tx1 = generate_one_fake_transaction(method="Net Banking", bank="ICICI", amount=1500.0, hour=14)
    print(f"ICICI NB Prob: {inc_tx1['calculated_probability']*100:.1f}% | Factors: {inc_tx1['audit_factors']}")
    assert any("ACTIVE INCIDENT" in f for f in inc_tx1['audit_factors'])

    print("\nPhase A2: During Recovery Phase (t=10s)")
    time.sleep(8)
    inc_tx2 = generate_one_fake_transaction(method="Net Banking", bank="ICICI", amount=1500.0, hour=14)
    print(f"ICICI NB Prob: {inc_tx2['calculated_probability']*100:.1f}% | Factors: {inc_tx2['audit_factors']}")
    assert any("INCIDENT RECOVERING" in f for f in inc_tx2['audit_factors'])

    print("\nPhase A3: After Incident Expiration (t=14s)")
    time.sleep(4)
    inc_tx3 = generate_one_fake_transaction(method="Net Banking", bank="ICICI", amount=1500.0, hour=14)
    print(f"ICICI NB Prob: {inc_tx3['calculated_probability']*100:.1f}% | Factors: {inc_tx3['audit_factors']}")
    assert not any("INCIDENT" in f for f in inc_tx3['audit_factors'])

    # 4. VERIFY UPGRADE D: Manual Simulator Endpoint behavior preserved
    print("\n--- [VERIFICATION D] Manual Failure Spike Injections (/api/simulate-failure) ---")
    spike_res = inject_failure_spike(merchant_id="ecommerce_store", method="UPI", bank=None, failure_count=5)
    print(f"Manual failure injection response: Injected={spike_res['injected_count']}, Updated Success Rate={spike_res['updated_success_rate']}%")
    assert spike_res['injected_count'] == 5

    print("\n" + "="*70)
    print("ALL VERIFICATION CHECKS COMPLETED SUCCESSFULLY!")
    print("="*70)

if __name__ == "__main__":
    test_upgrades()
