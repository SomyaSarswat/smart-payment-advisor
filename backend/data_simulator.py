import random
import time
from datetime import datetime
from collections import deque
from database import init_db, insert_transaction

# Master lists of domain data used for synthetic transaction generation
merchants = ["college_fee_portal", "ecommerce_store", "electricity_bill"]
methods = ["Credit Card", "Debit Card", "Net Banking", "UPI", "Wallet"]
banks = ["SBI", "HDFC", "ICICI", "Axis", "Kotak"]
devices = ["Android", "iOS", "Desktop"]

# Market share weights for realistic Indian transaction distribution (Upgrade 5)
BANK_WEIGHTS = {
    "SBI": 0.35,
    "HDFC": 0.30,
    "ICICI": 0.20,
    "Axis": 0.10,
    "Kotak": 0.05
}

METHOD_WEIGHTS = {
    "UPI": 0.45,
    "Credit Card": 0.20,
    "Debit Card": 0.15,
    "Net Banking": 0.12,
    "Wallet": 0.08
}

DEVICE_WEIGHTS = {
    "Android": 0.65,
    "iOS": 0.25,
    "Desktop": 0.10
}

MERCHANT_WEIGHTS = {
    "ecommerce_store": 0.50,
    "college_fee_portal": 0.30,
    "electricity_bill": 0.20
}

# Baseline bank reliability bounds for random walk drift (Upgrade 2)
BANK_RELIABILITY_BOUNDS = {
    "HDFC": (0.92, 0.96),
    "ICICI": (0.88, 0.92),
    "SBI": (0.84, 0.88),
    "Axis": (0.82, 0.88),
    "Kotak": (0.78, 0.88)
}

error_codes = [
    "issuer_timeout",
    "insufficient_funds",
    "otp_failed",
    "network_error",
    "bank_server_down"
]

def weighted_choice(choices_dict):
    """Helper to select item based on dictionary weight distribution."""
    items = list(choices_dict.keys())
    weights = list(choices_dict.values())
    return random.choices(items, weights=weights, k=1)[0]


class EcosystemSimulator:
    """
    Multi-factor, auditable payment ecosystem simulator.
    Tracks drifting bank baselines, autonomous bank+method outages,
    hourly rush patterns, rolling gateway load, and realistic per-method limits.
    """
    def __init__(self):
        # Initialize bank baselines at midpoint of target bounds
        self.bank_baselines = {
            bank: round((bounds[0] + bounds[1]) / 2.0, 4)
            for bank, bounds in BANK_RELIABILITY_BOUNDS.items()
        }
        
        # Active incidents store: (bank, method) -> dict
        # e.g., { ("SBI", "Credit Card"): {"start": t, "end": t+300, "recovery_start": t+240, "drop_depth": 0.30} }
        self.active_incidents = {}
        
        # Sliding history of transaction timestamps for load calculation (last 60s)
        self.tx_history = deque()
        self.last_incident_check = 0.0

    def drift_baselines(self):
        """Slow random walk drift for bank baselines within allowed bounds (Upgrade 2)."""
        for bank, bounds in BANK_RELIABILITY_BOUNDS.items():
            current = self.bank_baselines[bank]
            step = random.uniform(-0.003, +0.003)
            new_baseline = max(bounds[0], min(bounds[1], current + step))
            self.bank_baselines[bank] = round(new_baseline, 4)

    def trigger_incident(self, bank, method, duration_seconds=300, drop_depth=0.30):
        """Manually or autonomously register a bank+method incident (Upgrade 2)."""
        now = time.time()
        recovery_duration = duration_seconds * 0.25
        recovery_start = now + (duration_seconds - recovery_duration)
        end_time = now + duration_seconds
        
        self.active_incidents[(bank, method)] = {
            "bank": bank,
            "method": method,
            "start_time": now,
            "end_time": end_time,
            "recovery_start": recovery_start,
            "drop_depth": drop_depth
        }
        print(f"[INCIDENT TRIGGERED] {bank} {method} downtime started: target success {drop_depth*100:.0f}% for {duration_seconds//60}m")

    def check_incidents(self, now=None):
        """Check active incidents for expiration/recovery and schedule autonomous random incidents (Upgrade 2)."""
        if now is None:
            now = time.time()

        # 1. Clean up expired incidents and monitor active ones
        expired = []
        for key, inc in list(self.active_incidents.items()):
            if now >= inc["end_time"]:
                expired.append(key)
                print(f"[INCIDENT RECOVERED] {inc['bank']} {inc['method']} has fully returned to baseline reliability ({self.bank_baselines.get(inc['bank'], 0.85)*100:.1f}%).")
        
        for key in expired:
            del self.active_incidents[key]

        # 2. Autonomous Incident Scheduler (~30% chance every 15s if no active incident)
        if now - self.last_incident_check >= 15.0:
            self.last_incident_check = now
            if len(self.active_incidents) < 2 and random.random() < 0.30:  # ~30% chance every 15s
                # Pick a random bank and compatible method
                inc_bank = weighted_choice(BANK_WEIGHTS)
                inc_method = random.choice(["Credit Card", "Debit Card", "Net Banking", "UPI"])
                if (inc_bank, inc_method) not in self.active_incidents:
                    duration = random.randint(180, 420)  # 3 to 7 minutes for organic demo window
                    drop = round(random.uniform(0.20, 0.40), 2)  # severe drop to 20%-40%
                    self.trigger_incident(inc_bank, inc_method, duration_seconds=duration, drop_depth=drop)

    def get_hourly_rush_info(self, hour=None):
        """
        Calculates time-of-day rush multiplier, load penalty, and generation interval range (Upgrade 1 & Upgrade 4).
        - Peak (9-11 AM, 6-9 PM): 2.5x multiplier, -4% load penalty, fast interval (2.5-4s)
        - Off-peak (2-5 AM): 0.4x multiplier, 0 penalty, slow interval (8-12s)
        - Normal: 1.0x multiplier, 0 penalty, baseline interval (5-7s)
        """
        if hour is None:
            hour = datetime.now().hour

        if (9 <= hour <= 10) or (18 <= hour <= 20):
            return {
                "multiplier": 2.5,
                "load_penalty": -0.04,
                "interval_range": (2.5, 4.0),
                "desc": f"Peak Rush Hour ({hour:02d}:00)"
            }
        elif 2 <= hour <= 4:
            return {
                "multiplier": 0.4,
                "load_penalty": 0.0,
                "interval_range": (8.0, 12.0),
                "desc": f"Off-Peak Night Hour ({hour:02d}:00)"
            }
        else:
            return {
                "multiplier": 1.0,
                "load_penalty": 0.0,
                "interval_range": (5.0, 7.0),
                "desc": f"Normal Operating Hour ({hour:02d}:00)"
            }

    def get_current_generation_interval(self, hour=None):
        """Returns sleeping duration (seconds) based on rush multiplier (Upgrade 4)."""
        rush_info = self.get_hourly_rush_info(hour)
        low, high = rush_info["interval_range"]
        return round(random.uniform(low, high), 2)

    def calculate_transaction_probability(self, method, bank, hour, amount, now=None):
        """
        Multi-factor probability engine with full audit trail (Requirement 1).
        Every factor is explicitly logged and auditable.
        """
        if now is None:
            now = time.time()

        audit_factors = []
        forced_error_code = None

        # --- UPGRADE 3: REAL METHOD LIMITS & RISK CLIFFS ---
        if method == "UPI" and amount > 100000:
            audit_factors.append("UPI Amount > Rs.1,00,000 Hard Limit Cliff (95% Rejection)")
            return 0.05, audit_factors, "amount_limit_exceeded"

        if method == "Wallet" and amount > 20000:
            audit_factors.append("Wallet Amount > Rs.20,000 Hard Limit Cliff (95% Rejection)")
            return 0.05, audit_factors, "amount_limit_exceeded"

        # --- UPGRADE 2: DRIFTING BANK BASELINE ---
        if bank and bank in self.bank_baselines:
            base_prob = self.bank_baselines[bank]
            audit_factors.append(f"{bank} baseline reliability ({base_prob*100:.1f}%)")
        else:
            base_prob = 0.85
            audit_factors.append(f"Default method baseline ({base_prob*100:.1f}%)")

        prob = base_prob

        # --- UPGRADE 1: HOURLY RUSH PATTERN & PENALTY ---
        rush_info = self.get_hourly_rush_info(hour)
        if rush_info["load_penalty"] != 0:
            prob += rush_info["load_penalty"]
            audit_factors.append(f"{rush_info['desc']} load penalty ({rush_info['load_penalty']*100:+.1f}%)")
        else:
            audit_factors.append(f"{rush_info['desc']}")

        # --- UPGRADE 1: TIME-SENSITIVITY SPECIFIC MAINTENANCE PATTERNS ---
        if bank == "SBI" and method == "Credit Card" and (hour == 23 or hour <= 1):
            prob = min(prob, 0.40)
            audit_factors.append("SBI Credit Card late-night maintenance window (23:00-01:59 dip to 40%)")

        elif bank == "ICICI" and method == "Net Banking" and (2 <= hour <= 3):
            prob -= 0.30
            audit_factors.append("ICICI Net Banking early-morning batch maintenance (02:00-03:59 -30%)")

        elif bank == "Axis" and method == "Credit Card" and (0 <= hour <= 1):
            prob -= 0.25
            audit_factors.append("Axis Credit Card midnight reconciliation window (00:00-01:59 -25%)")

        # --- UPGRADE 3: HIGH VALUE CARD FRAUD-CHECK HOLD ---
        if method in ["Credit Card", "Debit Card"] and amount > 50000:
            prob -= 0.18
            audit_factors.append(f"High-value {method} (Rs.{amount:,.2f} > Rs.50,000) fraud check risk (-18.0%)")

        # --- UPGRADE 2: AUTONOMOUS INCIDENT OVERRIDE & RECOVERY ---
        inc_key = (bank, method)
        if inc_key in self.active_incidents:
            inc = self.active_incidents[inc_key]
            drop_depth = inc["drop_depth"]
            
            if now < inc["recovery_start"]:
                prob = drop_depth
                audit_factors.append(f"ACTIVE INCIDENT: {bank} {method} failure spike (drop to {drop_depth*100:.0f}%)")
            elif inc["recovery_start"] <= now < inc["end_time"]:
                # Smooth linear recovery
                progress = (now - inc["recovery_start"]) / (inc["end_time"] - inc["recovery_start"])
                current_level = drop_depth + progress * (base_prob - drop_depth)
                prob = current_level
                audit_factors.append(f"INCIDENT RECOVERING: {bank} {method} returning to baseline ({current_level*100:.1f}%)")

        # --- UPGRADE 4: SELF-GENERATED RECENT SYSTEM LOAD PENALTY ---
        # Clean history older than 60 seconds
        while self.tx_history and (now - self.tx_history[0]) > 60.0:
            self.tx_history.popleft()
        
        tpm = len(self.tx_history)
        if tpm >= 15:
            load_penalty = -0.03
            prob += load_penalty
            audit_factors.append(f"Gateway Rate-limiting Load ({tpm} TPM in 60s: {load_penalty*100:+.1f}%)")
        else:
            audit_factors.append(f"System Load Normal ({tpm} TPM)")

        # --- NATURAL MICRO-VARIATION NOISE ---
        noise = random.uniform(-0.02, +0.02)
        prob += noise
        audit_factors.append(f"Micro-variation ({noise*100:+.1f}%)")

        # Clamp between 5% and 98%
        final_prob = max(0.05, min(0.98, prob))
        return final_prob, audit_factors, forced_error_code

    def generate_one_fake_transaction(self, merchant=None, method=None, bank=None, amount=None, device=None, hour=None):
        """
        Generates 1 synthetic payment transaction using weighted selection,
        calculates explainable probability, updates drift & incidents, persists to DB,
        and logs auditable output line.
        """
        now = time.time()
        self.tx_history.append(now)

        # Update drift and check incidents
        self.drift_baselines()
        self.check_incidents(now)

        # 1. Weighted Selection if not explicitly provided
        # 25% chance to sample an active incident (bank, method) combo if any are active for audit visibility
        if self.active_incidents and method is None and bank is None and random.random() < 0.25:
            active_key = random.choice(list(self.active_incidents.keys()))
            bank, method = active_key
        else:
            if method is None:
                method = weighted_choice(METHOD_WEIGHTS)
            if method in ["Credit Card", "Debit Card", "Net Banking"]:
                if bank is None:
                    bank = weighted_choice(BANK_WEIGHTS)
            else:
                bank = None

        if merchant is None:
            merchant = weighted_choice(MERCHANT_WEIGHTS)
        if device is None:
            device = weighted_choice(DEVICE_WEIGHTS)

        # 2. Realistic Amount Distribution
        if amount is None:
            roll = random.random()
            if roll < 0.60:
                amount = round(random.uniform(100, 5000), 2)
            elif roll < 0.85:
                amount = round(random.uniform(5000, 45000), 2)
            else:
                amount = round(random.uniform(50000, 150000), 2)

        if hour is None:
            hour = datetime.now().hour

        # 3. Probability Calculation with Audit Factors
        prob, factors, forced_error = self.calculate_transaction_probability(method, bank, hour, amount, now)

        # 4. Status Determination
        is_success = random.random() < prob

        if is_success:
            status = "success"
            error_code = None
        else:
            status = "failed"
            if forced_error:
                error_code = forced_error
            elif method in ["Credit Card", "Debit Card"] and amount > 50000:
                error_code = random.choice(["fraud_check_hold", "issuer_timeout", "insufficient_funds"])
            else:
                error_code = random.choice(error_codes)

        # 5. Insert into Database
        inserted_id = insert_transaction(
            merchant_id=merchant,
            method=method,
            bank=bank,
            amount=amount,
            device=device,
            hour=hour,
            status=status,
            error_code=error_code
        )

        # 6. Auditable Output Logging
        bank_str = f"{bank} " if bank else ""
        method_display = f"{bank_str}{method}"
        status_display = "SUCCESS" if status == "success" else f"FAILED ({error_code})"
        factors_summary = " | ".join(factors)

        print(f"[LOG] {method_display} | Rs.{amount:,.2f} | {status_display} | Final Prob: {prob*100:.1f}% | Breakdown: [{factors_summary}]")

        return {
            "id": inserted_id,
            "merchant_id": merchant,
            "method": method,
            "bank": bank,
            "amount": amount,
            "device": device,
            "hour": hour,
            "status": status,
            "error_code": error_code,
            "timestamp": datetime.now().isoformat(),
            "calculated_probability": round(prob, 4),
            "audit_factors": factors
        }


# Global singleton instance
simulator = EcosystemSimulator()

def generate_base_success_probability(method, bank, hour, amount):
    """Legacy backward-compatibility wrapper function."""
    prob, _, _ = simulator.calculate_transaction_probability(method, bank, hour, amount)
    return prob

def generate_one_fake_transaction(merchant=None, method=None, bank=None, amount=None, device=None, hour=None):
    """Module-level function calling singleton simulator."""
    return simulator.generate_one_fake_transaction(merchant, method, bank, amount, device, hour)

def get_current_generation_interval(hour=None):
    """Module-level function returning current generation interval."""
    return simulator.get_current_generation_interval(hour)

def trigger_incident(bank, method, duration_seconds=300, drop_depth=0.30):
    """Module-level helper to trigger an incident for testing or demo."""
    simulator.trigger_incident(bank, method, duration_seconds, drop_depth)

def run_simulator(interval_seconds=None, duration_minutes=None):
    """Continuously generates transactions using dynamic interval."""
    init_db()
    print("Starting Multi-Factor Payment Ecosystem Simulator...")
    start_time = time.time()
    max_seconds = duration_minutes * 60 if duration_minutes is not None else None

    try:
        while True:
            if max_seconds is not None and (time.time() - start_time) >= max_seconds:
                print(f"Simulator completed target duration of {duration_minutes} minute(s).")
                break
                
            generate_one_fake_transaction()
            sleep_time = interval_seconds if interval_seconds else simulator.get_current_generation_interval()
            time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nSimulator stopped.")

if __name__ == "__main__":
    run_simulator()

