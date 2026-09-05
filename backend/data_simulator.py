import random
import time
from datetime import datetime
from database import init_db, insert_transaction

# Master lists of domain data used for synthetic transaction generation
merchants = ["college_fee_portal", "ecommerce_store", "electricity_bill"]
methods = ["Credit Card", "Debit Card", "Net Banking", "UPI", "Wallet"]
banks = ["SBI", "HDFC", "ICICI", "Axis", "Kotak"]
devices = ["Android", "iOS", "Desktop"]
error_codes = [
    "issuer_timeout",
    "insufficient_funds",
    "otp_failed",
    "network_error",
    "bank_server_down"
]

def generate_base_success_probability(method, bank, hour, amount):
    """
    Calculates a base success probability (0.0 to 1.0) based on realistic rule sets:
    - Default base: 0.85
    - SBI Credit Card late-night (11 PM - 1 AM): 0.40
    - UPI high value (> Rs. 50,000): 0.35
    - Wallet high value (> Rs. 20,000): 0.10
    - HDFC Net Banking high reliability: 0.93
    - Adds minor +/- 0.05 noise and clamps between 0.05 and 0.98.
    """
    prob = 0.85  # Default base probability

    # Rule 1: SBI Credit Card late-night server maintenance (23:00 to 01:59)
    if bank == "SBI" and method == "Credit Card" and (hour == 23 or hour <= 1):
        prob = 0.40

    # Rule 2: High amount UPI transactions (over Rs. 50,000 limit)
    elif method == "UPI" and amount > 50000:
        prob = 0.35

    # Rule 3: High amount Wallet transactions (over Rs. 20,000 limit)
    elif method == "Wallet" and amount > 20000:
        prob = 0.10

    # Rule 4: Highly reliable HDFC Net Banking
    elif bank == "HDFC" and method == "Net Banking":
        prob = 0.93

    # Add small natural random variation (+/- 0.05)
    noise = random.uniform(-0.05, 0.05)
    prob += noise

    # Clamp result between 0.05 (5%) and 0.98 (98%)
    clamped_prob = max(0.05, min(0.98, prob))
    return clamped_prob

def generate_one_fake_transaction():
    """
    Generates a single synthetic payment transaction and persists it to the SQLite database.
    Prints a formatted log line to stdout.
    """
    merchant = random.choice(merchants)
    method = random.choice(methods)
    device = random.choice(devices)

    # Assign a bank only if the payment method requires one
    if method in ["Credit Card", "Debit Card", "Net Banking"]:
        bank = random.choice(banks)
    else:
        bank = None

    # Amount distribution: 70% smaller everyday transactions, 30% larger payments
    if random.random() < 0.70:
        amount = round(random.uniform(500, 5000), 2)
    else:
        amount = round(random.uniform(20000, 100000), 2)

    # Current hour of day (0-23)
    current_hour = datetime.now().hour

    # Calculate success probability based on transaction context
    prob = generate_base_success_probability(method, bank, current_hour, amount)

    # Determine status based on probability roll
    is_success = random.random() < prob

    if is_success:
        status = "success"
        error_code = None
    else:
        status = "failed"
        error_code = random.choice(error_codes)

    # Insert into SQLite database
    insert_transaction(
        merchant_id=merchant,
        method=method,
        bank=bank,
        amount=amount,
        device=device,
        hour=current_hour,
        status=status,
        error_code=error_code
    )

    # Formatted log string
    bank_str = f"{bank} " if bank else ""
    method_display = f"{bank_str}{method}"
    status_display = "SUCCESS" if status == "success" else f"FAILED ({error_code})"

    print(f"[LOG] {method_display} | Rs.{amount:.2f} | {device} | {status_display}")

def run_simulator(interval_seconds=2, duration_minutes=None):
    """
    Continuously generates fake payment transactions at a set interval.
    
    Args:
        interval_seconds (int/float): Sleep duration between generated transactions.
        duration_minutes (int/float/None): Maximum run time in minutes. Runs indefinitely if None.
    """
    # Ensure database table exists before running
    init_db()
    
    print(f"Starting transaction simulator (Interval: {interval_seconds}s)... Press Ctrl+C to stop.")
    
    start_time = time.time()
    max_seconds = duration_minutes * 60 if duration_minutes is not None else None

    try:
        while True:
            # Check duration cutoff if specified
            if max_seconds is not None and (time.time() - start_time) >= max_seconds:
                print(f"Simulator completed target duration of {duration_minutes} minute(s).")
                break
                
            generate_one_fake_transaction()
            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\nSimulator stopped.")

if __name__ == "__main__":
    run_simulator(interval_seconds=2)
