import sqlite3
import os
import random
import time
from datetime import datetime, timedelta
import sys

# Ensure backend path is imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
from data_simulator import EcosystemSimulator, BANK_WEIGHTS, METHOD_WEIGHTS, DEVICE_WEIGHTS, MERCHANT_WEIGHTS, weighted_choice, error_codes

DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend", "payments.db"))

def generate_backfill(num_records=17000):
    print(f"[*] Resetting database at {DB_PATH} for optimal ML signal...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM transactions")
    conn.commit()
    
    sim = EcosystemSimulator()
    
    now = datetime.now()
    start_time = now - timedelta(days=10)
    
    rows = []
    print(f"[*] Generating {num_records} synthetic transactions with strong ML discriminative signals...")
    
    for i in range(num_records):
        progress_ratio = i / float(num_records)
        offset_seconds = int(progress_ratio * 10 * 86400) + random.randint(-600, 600)
        offset_seconds = max(0, min(10 * 86400, offset_seconds))
        
        tx_dt = start_time + timedelta(seconds=offset_seconds)
        tx_timestamp_str = tx_dt.isoformat()
        hour = tx_dt.hour
        
        merchant = weighted_choice(MERCHANT_WEIGHTS)
        method = weighted_choice(METHOD_WEIGHTS)
        
        if method in ["Credit Card", "Debit Card", "Net Banking"]:
            bank = weighted_choice(BANK_WEIGHTS)
        else:
            bank = None
            
        device = weighted_choice(DEVICE_WEIGHTS)
        
        # Method limit cliffs & value categories
        if method == "UPI":
            # 18% over 100k limit cliff
            amount = float(random.randint(102000, 150000)) if random.random() < 0.18 else float(random.randint(150, 95000))
        elif method == "Wallet":
            # 22% over 20k limit cliff
            amount = float(random.randint(21000, 48000)) if random.random() < 0.22 else float(random.randint(100, 19000))
        elif method in ["Credit Card", "Debit Card"]:
            # 30% high value transactions (> 50k)
            amount = float(random.randint(51000, 125000)) if random.random() < 0.30 else float(random.randint(500, 48000))
        else:
            amount = float(random.randint(500, 75000))
            
        prob, audit_factors, forced_err = sim.calculate_transaction_probability(
            method=method,
            bank=bank,
            hour=hour,
            amount=amount,
            now=time.mktime(tx_dt.timetuple())
        )
        
        # Additional discriminative domain patterns
        if bank == "SBI" and method == "Credit Card" and (hour >= 22 or hour <= 2):
            prob = 0.25
            forced_err = "bank_server_down"
        elif bank == "ICICI" and method == "Net Banking" and (1 <= hour <= 4):
            prob = 0.30
            forced_err = "network_error"
        elif bank == "Kotak" and method == "Debit Card" and (13 <= hour <= 17):
            prob = 0.28
            forced_err = "issuer_timeout"
        elif bank == "Axis" and method == "Credit Card" and (hour == 0 or hour == 1):
            prob = 0.32
            forced_err = "bank_server_down"
            
        is_success = random.random() < prob
        if is_success:
            status = "success"
            err_code = None
        else:
            status = "failed"
            err_code = forced_err if forced_err else random.choice(error_codes)
            
        rows.append((merchant, method, bank, amount, device, hour, status, err_code, tx_timestamp_str))
        
    print(f"[*] Batch inserting {len(rows)} records into payments.db...")
    cursor.executemany("""
        INSERT INTO transactions (merchant_id, method, bank, amount, device, hour, status, error_code, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, rows)
    
    conn.commit()
    
    cursor.execute("SELECT COUNT(*), MIN(timestamp), MAX(timestamp) FROM transactions")
    count, min_ts, max_ts = cursor.fetchone()
    print("==================================================")
    print(f"[SUCCESS] High-Signal Dataset Backfill Complete!")
    print(f"Total Transactions in DB : {count}")
    print(f"Oldest Timestamp         : {min_ts}")
    print(f"Newest Timestamp         : {max_ts}")
    print("==================================================")
    
    conn.close()

if __name__ == "__main__":
    generate_backfill(17000)
