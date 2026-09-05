from database import get_recent_transactions

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

def calculate_success_rate(transactions):
    """
    Calculates the success rate percentage from a list of transaction dictionaries.
    Returns float percentage (0.0 to 100.0) or None if transaction list is empty.
    """
    if not transactions:
        return None

    successful_count = sum(1 for tx in transactions if tx.get("status") == "success")
    total_count = len(transactions)
    
    return (successful_count / total_count) * 100.0

def get_success_rate_for_combo(method, bank, merchant_id, amount, recent_2h_data, recent_24h_data, all_historical_data):
    """
    Computes live success rate using a progressive multi-window fallback chain:
    1. Short-term (last 2h) data for specific merchant & amount range (+/- 30%)
    2. Short-term (last 2h) data for specific merchant & method/bank combo
    3. Medium-term (last 24h) data for specific merchant & method/bank combo
    4. Historical dataset for specific merchant & method/bank combo
    5. Overall dataset for method/bank combo across any merchant
    6. Platform default fallback (75.0%) used ONLY when 0 records exist anywhere in DB
    """
    amount_min = amount * 0.70
    amount_max = amount * 1.30

    # Step 1: 2-hour window with merchant + method + bank + amount range
    matches_2h_strict = [
        tx for tx in recent_2h_data
        if tx.get("method") == method
        and (tx.get("bank") == bank or (bank is None and tx.get("bank") is None))
        and tx.get("merchant_id") == merchant_id
        and amount_min <= tx.get("amount", 0) <= amount_max
    ]
    if len(matches_2h_strict) >= 3:
        return calculate_success_rate(matches_2h_strict), len(matches_2h_strict), "high"

    # Step 2: 2-hour window with merchant + method + bank
    matches_2h = [
        tx for tx in recent_2h_data
        if tx.get("method") == method
        and (tx.get("bank") == bank or (bank is None and tx.get("bank") is None))
        and tx.get("merchant_id") == merchant_id
    ]
    if len(matches_2h) >= 3:
        return calculate_success_rate(matches_2h), len(matches_2h), "high"

    # Step 3: 24-hour window with merchant + method + bank
    matches_24h = [
        tx for tx in recent_24h_data
        if tx.get("method") == method
        and (tx.get("bank") == bank or (bank is None and tx.get("bank") is None))
        and tx.get("merchant_id") == merchant_id
    ]
    if len(matches_24h) >= 3:
        return calculate_success_rate(matches_24h), len(matches_24h), "medium"

    # Step 4: Historical window with merchant + method + bank
    matches_hist = [
        tx for tx in all_historical_data
        if tx.get("method") == method
        and (tx.get("bank") == bank or (bank is None and tx.get("bank") is None))
        and tx.get("merchant_id") == merchant_id
    ]
    if len(matches_hist) >= 2:
        return calculate_success_rate(matches_hist), len(matches_hist), "historical"

    # Step 5: Overall dataset with method + bank across all merchants
    matches_broad = [
        tx for tx in all_historical_data
        if tx.get("method") == method
        and (tx.get("bank") == bank or (bank is None and tx.get("bank") is None))
    ]
    if len(matches_broad) >= 2:
        return calculate_success_rate(matches_broad), len(matches_broad), "broad"

    # Step 6: Cold start default (zero database records)
    return 75.0, 0, "estimated"

def generate_reason(method, bank, current_rate, baseline_rate, confidence_level):
    """
    Generates a human-readable explanation for a payment option's performance.
    """
    if confidence_level == "estimated":
        return "Limited historical data — displaying estimated baseline"

    if current_rate >= 90.0:
        return "High reliability & optimal success rate right now"
    elif current_rate <= 40.0:
        return "Critical downtime / server maintenance detected — high risk of failure"
    elif current_rate <= 65.0:
        return "Experiencing elevated transaction failures — proceed with caution"
    else:
        return "Stable connection & normal performance"

def get_recommendations(merchant_id, amount, device, available_methods_banks):
    """
    Main recommendation entry point.
    Ranks given available (method, bank) options based on dynamic live success rates.

    Args:
        merchant_id (str): Merchant identifier (e.g. 'college_fee_portal')
        amount (float): Payment transaction amount
        device (str): User device ('Android', 'iOS', 'Desktop')
        available_methods_banks (list): List of (method, bank) tuples

    Returns:
        List of dictionaries sorted by success_rate in descending order.
    """
    # Fetch short-term (2h), medium-term (24h), and full historical transaction datasets
    recent_2h_data = get_recent_transactions(hours_lookback=2)
    recent_24h_data = get_recent_transactions(hours_lookback=24)
    all_historical_data = get_recent_transactions(hours_lookback=24 * 365)

    recommendations = []

    for method, bank in available_methods_banks:
        # Calculate current success rate with multi-window fallback chain
        current_rate, data_points, confidence = get_success_rate_for_combo(
            method, bank, merchant_id, amount, recent_2h_data, recent_24h_data, all_historical_data
        )

        # Calculate baseline rate
        baseline_rate, _, _ = get_success_rate_for_combo(
            method, bank, merchant_id, amount, recent_24h_data, recent_24h_data, all_historical_data
        )

        # Generate contextual reason statement
        reason = generate_reason(method, bank, current_rate, baseline_rate, confidence)

        # Lookup fee in INR
        fee = METHOD_BANK_FEES.get((method, bank), 0)

        recommendations.append({
            "method": method,
            "bank": bank,
            "success_rate": round(current_rate, 1),
            "fee": fee,
            "reason": reason,
            "confidence_level": confidence,
            "is_recommended": False
        })

    # Sort options by success_rate descending (highest success rate first)
    recommendations.sort(key=lambda x: x["success_rate"], reverse=True)

    # Mark the top-ranked option as recommended
    if recommendations:
        recommendations[0]["is_recommended"] = True

    return recommendations

if __name__ == "__main__":
    # Test example execution
    test_merchant = "college_fee_portal"
    test_amount = 18000
    test_device = "Android"
    test_options = [
        ("Credit Card", "SBI"),
        ("Credit Card", "HDFC"),
        ("Net Banking", "HDFC"),
        ("UPI", None),
        ("Wallet", None)
    ]

    print(f"--- Recommendations for {test_merchant} | Amount: Rs. {test_amount} ---")
    results = get_recommendations(test_merchant, test_amount, test_device, test_options)

    for rank, item in enumerate(results, start=1):
        bank_str = f" ({item['bank']})" if item['bank'] else ""
        recommended_flag = " [RECOMMENDED]" if item['is_recommended'] else ""
        print(f"Rank {rank}: {item['method']}{bank_str}{recommended_flag}")
        print(f"        Success Rate: {item['success_rate']}% | Fee: Rs. {item['fee']} | Confidence: {item['confidence_level']}")
        print(f"        Reason: {item['reason']}\n")

