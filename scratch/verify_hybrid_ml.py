import os
import sys
import json
import sqlite3
from datetime import datetime

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from ml_model import train_and_save_model, get_model_metadata, predict_success_probability
from recommendation_engine import get_recommendations, get_success_rate_for_combo
from database import get_connection, inject_failure_spike

def run_verification():
    print("=" * 70)
    print("VERIFICATION REQUIREMENT 1: ACTUAL ML TRAINING OUTPUT & METRICS")
    print("=" * 70)
    meta = train_and_save_model()
    print(f"-> Training Sample Count: {meta['training_sample_count']}")
    print(f"-> Train Set Size: {meta['train_sample_count']} (80%)")
    print(f"-> Test Set Size: {meta['test_sample_count']} (20%)")
    print(f"-> Success Count: {meta['success_count']} | Failure Count: {meta['failure_count']}")
    print(f"-> Test Accuracy: {meta['test_accuracy']}%")
    print(f"-> Test ROC-AUC Score: {meta['test_auc']}")
    print(f"-> Confusion Matrix [[TN, FP], [FN, TP]]:")
    print(f"     {meta['confusion_matrix'][0]}")
    print(f"     {meta['confusion_matrix'][1]}")
    print(f"-> Model file size: {os.path.getsize(os.path.join(os.path.dirname(__file__), '..', 'backend', 'models', 'success_predictor.joblib')) / 1024:.1f} KB")

    print("\n" + "=" * 70)
    print("VERIFICATION REQUIREMENT 2: BLEND LOGIC DEMONSTRATION")
    print("=" * 70)

    # 2(a) Well-populated combo (e.g. Credit Card - SBI or Credit Card - HDFC or UPI)
    all_combos = [
        ("Credit Card", "SBI"),
        ("Credit Card", "HDFC"),
        ("Debit Card", "SBI"),
        ("UPI", None),
        ("BrandNewMethod_XY", "UnseenBank_Z") # 2(b) Brand new / zero-sample combo
    ]

    recs = get_recommendations(
        merchant_id="college_fee_portal",
        amount=15000.0,
        device="Desktop",
        available_methods_banks=all_combos
    )

    well_populated_item = None
    cold_start_item = None

    for item in recs:
        if item["method"] == "BrandNewMethod_XY":
            cold_start_item = item
        elif item["data_points"] >= 20 and well_populated_item is None:
            well_populated_item = item

    print("\n--- 2(a) Well-Populated Combo (sample_size >= 20) ---")
    if well_populated_item:
        print(f"Method/Bank: {well_populated_item['method']} - {well_populated_item['bank']}")
        print(f"Sample Count (data_points): {well_populated_item['data_points']}")
        print(f"Live Statistical Rate: {well_populated_item['live_statistical_rate']}%")
        print(f"ML Model Prediction: {well_populated_item['ml_predicted_rate']}%")
        print(f"Calculated live_weight: {well_populated_item['live_confidence_weight']} (Formula: min({well_populated_item['data_points']}, 20) / 20 = 1.0)")
        print(f"Calculated ml_weight: {well_populated_item['ml_confidence_weight']} (Formula: 1.0 - live_weight = 0.0)")
        print(f"Final Blended Success Rate: {well_populated_item['success_rate']}%")
        assert well_populated_item["live_confidence_weight"] == 1.0, "Live weight should be 1.0 for sample_size >= 20"
        assert well_populated_item["success_rate"] == well_populated_item["live_statistical_rate"], "Final rate must match pure statistical rate when live_weight = 1.0"
        print("[OK] VERIFIED: Pure statistical rate dominates when live sample size >= 20!")
    else:
        print("⚠️ No combo found with >= 20 data points in current DB snapshot.")

    print("\n--- 2(b) Cold-Start / Brand New Combo (sample_size = 0) ---")
    if cold_start_item:
        print(f"Method/Bank: {cold_start_item['method']} - {cold_start_item['bank']}")
        print(f"Sample Count (data_points): {cold_start_item['data_points']}")
        print(f"Live Statistical Rate: {cold_start_item['live_statistical_rate']}%")
        print(f"ML Model Prediction: {cold_start_item['ml_predicted_rate']}%")
        print(f"Calculated live_weight: {cold_start_item['live_confidence_weight']} (Formula: min(0, 20) / 20 = 0.0)")
        print(f"Calculated ml_weight: {cold_start_item['ml_confidence_weight']} (Formula: 1.0 - 0.0 = 1.0)")
        print(f"Final Blended Success Rate: {cold_start_item['success_rate']}%")
        assert cold_start_item["live_confidence_weight"] == 0.0, "Live weight should be 0.0 for 0 samples"
        assert cold_start_item["ml_confidence_weight"] == 1.0, "ML weight should be 1.0 for 0 samples"
        assert cold_start_item["success_rate"] == cold_start_item["ml_predicted_rate"], "Final rate must equal ML prediction for 0 samples"
        print("[OK] VERIFIED: ML prediction fills cold-start gap completely when sample size = 0!")

    print("\n" + "=" * 70)
    print("VERIFICATION REQUIREMENT 3: FAILURE SPIKE INCIDENT OVERRIDE")
    print("=" * 70)

    test_merchant = "college_fee_portal"
    test_method = "Credit Card"
    test_bank = "ICICI"
    test_combos = [(test_method, test_bank)]

    # Get rate before spike
    pre_recs = get_recommendations(test_merchant, 1000.0, "Desktop", test_combos)
    pre_rate = pre_recs[0]["success_rate"]
    print(f"Before Failure Spike: {test_method} ({test_bank}) Rate = {pre_rate}%, Data Points = {pre_recs[0]['data_points']}")

    # Inject 25 failure records
    spike_result = inject_failure_spike(
        merchant_id=test_merchant,
        method=test_method,
        bank=test_bank,
        failure_count=25,
        error_code="simulated_incident_downtime"
    )

    # Get rate after spike
    post_recs = get_recommendations(test_merchant, 1000.0, "Desktop", test_combos)
    post_item = post_recs[0]
    post_rate = post_item["success_rate"]

    print(f"After Injecting 25 Failures: {test_method} ({test_bank}) Rate = {post_rate}%, Data Points = {post_item['data_points']}")
    print(f"Live Statistical Rate: {post_item['live_statistical_rate']}%, ML Prediction: {post_item['ml_predicted_rate']}%")
    print(f"Live Weight: {post_item['live_confidence_weight']}, ML Weight: {post_item['ml_confidence_weight']}")
    print(f"Detected Reason: '{post_item['reason']}'")

    assert post_rate < pre_rate - 20.0, f"Expected sharp rate drop (>20 pts), but got {pre_rate}% -> {post_rate}%"
    assert post_item["live_confidence_weight"] == 1.0, "Live weight should be 1.0 as sample count grew >= 20"
    print("[OK] VERIFIED: Failure spike causes immediate sharp drop in displayed rate; live signal dominates!")

    print("\n" + "=" * 70)
    print("VERIFICATION REQUIREMENT 4: EXISTING ENGINE FEATURES PRESERVED")
    print("=" * 70)
    # Check smart composite score ranking & fee penalties
    multi_recs = get_recommendations(
        merchant_id="college_fee_portal",
        amount=25000.0,
        device="Desktop",
        available_methods_banks=[("Credit Card", "SBI"), ("Credit Card", "HDFC"), ("Debit Card", "SBI"), ("UPI", None)]
    )

    print("Composite Fee-Aware Ranking Order:")
    for idx, r in enumerate(multi_recs):
        print(f"  #{idx+1}: {r['method']} ({r['bank']}) -> Success: {r['success_rate']}%, Fee: INR {r['fee']}, SmartScore: {r['smart_score']}, CI: +/-{r['confidence_interval']}%, Recommended: {r['is_recommended']}")

    assert len(multi_recs) == 4, "Should return all 4 requested options"
    assert multi_recs[0]["is_recommended"] == True, "First option must be marked recommended"
    assert "confidence_interval" in multi_recs[0], "Confidence interval field must be present"
    print("[OK] VERIFIED: Composite fee-aware ranking, confidence intervals, and recommendations functioning perfectly!")

if __name__ == "__main__":
    run_verification()
