import math
from functools import lru_cache
from datetime import datetime
from database import get_windowed_stats_sql, get_windowed_transactions_decay, get_recent_transactions
from ml_model import predict_success_probability

# Transaction fees in INR mapped by (method, bank) tuple
METHOD_BANK_FEES = {
    # Credit Card fees
    ("Credit Card", "SBI"): 0,
    ("Credit Card", "HDFC"): 15,
    ("Credit Card", "ICICI"): 10,
    ("Credit Card", "Axis"): 10,
    ("Credit Card", "Kotak"): 10,
    # Debit Card fees
    ("Debit Card", "SBI"): 0,
    ("Debit Card", "HDFC"): 0,
    ("Debit Card", "ICICI"): 0,
    ("Debit Card", "Axis"): 0,
    ("Debit Card", "Kotak"): 0,
    # Net Banking fees
    ("Net Banking", "SBI"): 5,
    ("Net Banking", "HDFC"): 5,
    ("Net Banking", "ICICI"): 5,
    ("Net Banking", "Axis"): 5,
    ("Net Banking", "Kotak"): 5,
    # UPI & Wallet fees (no bank)
    ("UPI", None): 0,
    ("Wallet", None): 2,
}

# UPGRADE 2: Exponential Decay Constant
# a 5-minute-old transaction has ~2x the influence of a 30-minute-old transaction:
# exp(-c * 5) / exp(-c * 30) = exp(25 * c) = 2 => c = ln(2) / 25 ≈ 0.027725887
DECAY_CONSTANT = 0.027725887

def calculate_exponential_decay_rate(rows, now=None):
    """
    UPGRADE 2: Computes recency-weighted success rate using exponential decay:
      weight_i = exp(-decay_constant * age_in_minutes)
      weighted_success_rate = sum(weight_i * is_success_i) / sum(weight_i)
    """
    if not rows:
        return None, 0

    if now is None:
        now = datetime.now()

    weighted_sum = 0.0
    total_weight = 0.0

    for row in rows:
        try:
            tx_dt = datetime.fromisoformat(row["timestamp"])
            age_mins = max(0.0, (now - tx_dt).total_seconds() / 60.0)
        except Exception:
            age_mins = 0.0

        w = math.exp(-DECAY_CONSTANT * age_mins)
        is_success = 1.0 if row.get("status") == "success" else 0.0

        weighted_sum += w * is_success
        total_weight += w

    if total_weight <= 0:
        return None, len(rows)

    weighted_rate = (weighted_sum / total_weight) * 100.0
    return weighted_rate, len(rows)

def calculate_confidence_interval(success_rate, data_points, confidence_level):
    """
    UPGRADE 4: Computes confidence interval margin of error (± X%) using standard error approximation:
      SE = sqrt(p * (1 - p) / n)
      ME = 1.96 * SE * 100
    """
    if confidence_level == "estimated" or data_points < 3:
        return 15.0
    
    p = (success_rate or 75.0) / 100.0
    p_clamped = max(0.05, min(0.95, p))
    se = math.sqrt((p_clamped * (1.0 - p_clamped)) / data_points)
    me = 1.96 * se * 100.0
    return round(max(2.0, min(25.0, me)), 1)

@lru_cache(maxsize=512)
def _get_success_rate_cached(method, bank, merchant_id):
    decay_rows = get_windowed_transactions_decay(merchant_id, method, bank, hours_lookback=2)
    if len(decay_rows) >= 3:
        decay_rate, count = calculate_exponential_decay_rate(decay_rows)
        return decay_rate, count, "high"

    stats_24h = get_windowed_stats_sql(merchant_id, method, bank, hours_lookback=24)
    if stats_24h["total_count"] >= 3:
        return stats_24h["success_rate"], stats_24h["total_count"], "medium"

    stats_broad = get_windowed_stats_sql(merchant_id=None, method=method, bank=bank, hours_lookback=24 * 365)
    if stats_broad["total_count"] >= 2:
        return stats_broad["success_rate"], stats_broad["total_count"], "broad"

    return 75.0, 0, "estimated"


def get_success_rate_for_combo(method, bank, merchant_id, amount=None):
    """
    UPGRADE 1 & 2:
    Computes live recency-weighted success rate using direct SQL aggregate window queries
    and exponential decay time-weighting.
    """
    return _get_success_rate_cached(method, bank, merchant_id)

@lru_cache(maxsize=512)
def get_baseline_rate(method, bank, merchant_id):
    """
    UPGRADE 3: Computes historical baseline success rate for anomaly detection.
    """
    stats_merchant_hist = get_windowed_stats_sql(merchant_id, method, bank, hours_lookback=24 * 365)
    if stats_merchant_hist["total_count"] >= 3 and stats_merchant_hist["success_rate"] is not None:
        return stats_merchant_hist["success_rate"]
    
    stats_broad = get_windowed_stats_sql(None, method, bank, hours_lookback=24 * 365)
    if stats_broad["total_count"] >= 2 and stats_broad["success_rate"] is not None:
        return stats_broad["success_rate"]

    return 80.0

def generate_reason(method, bank, current_rate, baseline_rate, confidence_level, data_points=0):
    """
    UPGRADE 3: Statistical anomaly detection comparing current rate vs method's own baseline rate.
    Flags genuine downtime spikes when current rate drops > 30% below baseline.
    """
    if confidence_level == "estimated" or data_points == 0:
        return "ML-supported initial estimate — limited live data"

    deviation = baseline_rate - current_rate if (baseline_rate is not None and current_rate is not None) else 0.0

    if data_points >= 5 and deviation >= 30.0:
        return f"Critical downtime detected ({round(deviation, 1)} pts below baseline)"
    elif data_points >= 5 and deviation >= 15.0:
        return f"Degraded performance ({round(deviation, 1)} pts below baseline)"
    elif current_rate >= 90.0:
        return "High reliability — optimal success rate right now"
    elif current_rate >= 75.0:
        return "Stable performance — consistently reliable"
    elif current_rate >= 60.0:
        return "Elevated failure rate — proceed with awareness"
    elif current_rate >= 40.0:
        return "Degraded performance — consider alternative method"
    else:
        return "Critical downtime detected — high risk of failure"

def get_sample_info(confidence_level, data_points, ml_weight=0.0):
    """
    Generates data-driven sample window information string including ML blend context.
    """
    if data_points == 0:
        return "100% ML Model Prediction (Cold Start)"

    window_map = {
        "high": "last 2 hours",
        "medium": "last 24 hours",
        "historical": "merchant historical data",
        "broad": "platform historical average"
    }
    window_str = window_map.get(confidence_level, "recent data")
    tx_str = "transaction" if data_points == 1 else "transactions"
    
    if ml_weight > 0:
        live_pct = int(round((1.0 - ml_weight) * 100))
        ml_pct = int(round(ml_weight * 100))
        return f"Based on {data_points} {tx_str} ({live_pct}% live + {ml_pct}% ML)"
    
    return f"Based on {data_points} {tx_str} in the {window_str}"

# In-Memory Cache for tracking previous success rates per (merchant_id, method, bank)
# Resets on backend restart (used for demo & real-time trend arrows tracking)
PREVIOUS_RATES_CACHE = {}

def get_recommendations(merchant_id, amount, device, available_methods_banks, hour=None, day_of_week=None):
    """
    Main recommendation engine entry point.
    Ranks payment options using a HYBRID system:
      - Live recency-weighted statistical rate (SQL window aggregation & exponential decay)
      - Supervised ML model prediction probability (GradientBoostingClassifier)
      - Confidence-weighted blending:
          live_weight = min(sample_size, 20) / 20
          ml_weight = 1 - live_weight
          final_rate = (live_weight * live_statistical_rate) + (ml_weight * ml_predicted_prob * 100)
    """
    now_dt = datetime.now()
    now_iso = now_dt.isoformat()
    hour_val = hour if hour is not None else now_dt.hour
    dow_val = day_of_week if day_of_week is not None else now_dt.weekday()
    recommendations = []

    for method, bank in available_methods_banks:
        # 1. Live statistical rate calculation
        live_rate, data_points, confidence = get_success_rate_for_combo(
            method, bank, merchant_id, amount
        )

        # 2. Supervised ML Model Prediction Probability (0.0 to 1.0 -> 0% to 100%)
        ml_prob = predict_success_probability(
            method=method,
            bank=bank,
            hour=hour_val,
            day_of_week=dow_val,
            amount=amount,
            merchant_id=merchant_id
        )
        ml_predicted_rate = ml_prob * 100.0

        # 3. Confidence-weighted hybrid blend calculation
        sample_size = data_points
        live_weight = min(sample_size, 20) / 20.0
        ml_weight = 1.0 - live_weight
        final_rate = (live_weight * live_rate) + (ml_weight * ml_predicted_rate)

        # Baseline rate for statistical anomaly detection
        baseline_rate = get_baseline_rate(method, bank, merchant_id)

        # Contextual reason statement
        reason = generate_reason(method, bank, final_rate, baseline_rate, confidence, data_points)
        sample_info = get_sample_info(confidence, data_points, ml_weight)

        # Confidence interval calculation (± X%)
        conf_interval = calculate_confidence_interval(final_rate, data_points, confidence)

        # Fee lookup
        fee = METHOD_BANK_FEES.get((method, bank), 0)

        # Smart Composite Score: Blended Success Rate - Bounded Fee Penalty (Tie-breaker) + Data Confidence Bonus
        # Fee penalty is scaled down (0.03x) so a Rs.15 fee is only a 0.45 pt penalty, ensuring success rate remains primary.
        fee_penalty = round(fee * 0.03, 2)
        sample_bonus = min(data_points, 10) * 0.2
        smart_score = round(final_rate - fee_penalty + sample_bonus, 2)

        # Track trend indicator against in-memory previous rate cache
        cache_key = (merchant_id, method, bank)
        prev_rate = PREVIOUS_RATES_CACHE.get(cache_key)

        if prev_rate is not None:
            diff = final_rate - prev_rate
            rate_change = round(diff, 1)
            if diff > 0.5:
                trend = "up"
            elif diff < -0.5:
                trend = "down"
            else:
                trend = "stable"
        else:
            # First calculation for this combo: compare against baseline
            diff = final_rate - baseline_rate
            rate_change = round(diff, 1)
            if diff > 1.0:
                trend = "up"
            elif diff < -1.0:
                trend = "down"
            else:
                trend = "stable"

        # Update in-memory cache with current success rate
        PREVIOUS_RATES_CACHE[cache_key] = final_rate

        recommendations.append({
            "method": method,
            "bank": bank,
            "success_rate": round(final_rate, 1),
            "live_statistical_rate": round(live_rate, 1),
            "ml_predicted_rate": round(ml_predicted_rate, 1),
            "ml_confidence_weight": round(ml_weight, 2),
            "live_confidence_weight": round(live_weight, 2),
            "fee": fee,
            "reason": reason,
            "sample_info": sample_info,
            "data_points": data_points,
            "confidence_level": confidence,
            "confidence_interval": conf_interval,
            "smart_score": smart_score,
            "trend": trend,
            "previous_rate": round(prev_rate, 1) if prev_rate is not None else round(baseline_rate, 1),
            "rate_change": rate_change,
            "computed_at": now_iso,
            "is_recommended": False
        })

    # Sort options by smart_score descending (Primary: Success Rate, Secondary: Low Fee, Tertiary: High Volume)
    recommendations.sort(key=lambda x: (x["smart_score"], x["success_rate"], -x["fee"]), reverse=True)

    # Mark top ranked option
    if recommendations:
        recommendations[0]["is_recommended"] = True

    return recommendations

