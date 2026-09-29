import os
import sys
import json
import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.utils.class_weight import compute_sample_weight
from sklearn.metrics import (
    accuracy_score, roc_auc_score, confusion_matrix,
    precision_score, recall_score, f1_score, precision_recall_curve, roc_curve
)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
from ml_model import extract_features_from_db

def evaluate_predictions(y_true, y_pred, y_proba):
    """Computes comprehensive evaluation metrics."""
    acc = accuracy_score(y_true, y_pred)
    auc = roc_auc_score(y_true, y_proba)
    cm = confusion_matrix(y_true, y_pred)  # [[TN, FP], [FN, TP]]
    tn, fp, fn, tp = cm.ravel()

    # Class 0: Failed, Class 1: Success
    fail_rec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
    fail_prec = tn / (tn + fn) if (tn + fn) > 0 else 0.0
    fail_f1 = (2 * fail_prec * fail_rec) / (fail_prec + fail_rec) if (fail_prec + fail_rec) > 0 else 0.0

    succ_rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    succ_prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    succ_f1 = (2 * succ_prec * succ_rec) / (succ_prec + succ_rec) if (succ_prec + succ_rec) > 0 else 0.0

    return {
        "accuracy": round(acc * 100, 2),
        "roc_auc": round(auc, 4),
        "confusion_matrix": cm.tolist(),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
        "fail_recall": round(fail_rec * 100, 2),
        "fail_precision": round(fail_prec * 100, 2),
        "fail_f1": round(fail_f1, 4),
        "succ_recall": round(succ_rec * 100, 2),
        "succ_precision": round(succ_prec * 100, 2),
        "succ_f1": round(succ_f1, 4),
    }

def run_experiments():
    df = extract_features_from_db()
    feature_cols = ["method", "bank", "hour_of_day", "day_of_week", "is_peak_hour", "amount_bucket", "merchant_id"]
    X = df[feature_cols]
    y = df["label"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    categorical_cols = ["method", "bank", "amount_bucket", "merchant_id"]
    numeric_cols = ["hour_of_day", "day_of_week", "is_peak_hour"]

    # Preprocessor pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical_cols),
            ("num", StandardScaler(), numeric_cols)
        ]
    )

    X_train_trans = preprocessor.fit_transform(X_train)
    X_test_trans = preprocessor.transform(X_test)

    # ==========================================
    # 1. BASELINE (Default GradientBoosting 0.5 threshold)
    # ==========================================
    gb_baseline = GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, max_depth=4, random_state=42)
    gb_baseline.fit(X_train_trans, y_train)

    y_pred_base = gb_baseline.predict(X_test_trans)
    y_proba_base = gb_baseline.predict_proba(X_test_trans)[:, 1]
    baseline_metrics = evaluate_predictions(y_test, y_pred_base, y_proba_base)

    # ==========================================
    # 2. OPTION A1: Sample-Weighted GradientBoosting
    # ==========================================
    sample_weights = compute_sample_weight("balanced", y_train)
    gb_weighted = GradientBoostingClassifier(n_estimators=100, learning_rate=0.1, max_depth=4, random_state=42)
    gb_weighted.fit(X_train_trans, y_train, sample_weight=sample_weights)

    y_pred_optA1 = gb_weighted.predict(X_test_trans)
    y_proba_optA1 = gb_weighted.predict_proba(X_test_trans)[:, 1]
    optA1_metrics = evaluate_predictions(y_test, y_pred_optA1, y_proba_optA1)

    # ==========================================
    # 3. OPTION A2: RandomForest with class_weight='balanced'
    # ==========================================
    rf_balanced = RandomForestClassifier(n_estimators=100, class_weight="balanced", random_state=42)
    rf_balanced.fit(X_train_trans, y_train)

    y_pred_optA2 = rf_balanced.predict(X_test_trans)
    y_proba_optA2 = rf_balanced.predict_proba(X_test_trans)[:, 1]
    optA2_metrics = evaluate_predictions(y_test, y_pred_optA2, y_proba_optA2)

    # ==========================================
    # 4. OPTION B: Threshold Tuning on Baseline Model (Train set optimization)
    # ==========================================
    y_train_proba = gb_baseline.predict_proba(X_train_trans)[:, 1]
    
    # Tune threshold to maximize F1 of failed class (label 0)
    # Note: probability of failure is (1 - p_success)
    # Prediction is failure if p_success < threshold
    thresholds = np.linspace(0.1, 0.9, 81)
    best_thresh_b = 0.5
    best_f1_b = 0.0

    for th in thresholds:
        pred = (y_train_proba >= th).astype(int)
        # Calculate failure F1
        tn, fp, fn, tp = confusion_matrix(y_train, pred).ravel()
        fail_rec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        fail_prec = tn / (tn + fn) if (tn + fn) > 0 else 0.0
        fail_f1 = (2 * fail_prec * fail_rec) / (fail_prec + fail_rec) if (fail_prec + fail_rec) > 0 else 0.0
        if fail_f1 > best_f1_b:
            best_f1_b = fail_f1
            best_thresh_b = th

    y_pred_optB = (y_proba_base >= best_thresh_b).astype(int)
    optB_metrics = evaluate_predictions(y_test, y_pred_optB, y_proba_base)
    optB_metrics["threshold"] = round(best_thresh_b, 3)

    # ==========================================
    # 5. OPTION A+B (Weighted Model + Threshold Tuning on Train Set)
    # ==========================================
    y_train_proba_w = gb_weighted.predict_proba(X_train_trans)[:, 1]
    best_thresh_ab = 0.5
    best_f1_ab = 0.0

    for th in thresholds:
        pred = (y_train_proba_w >= th).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_train, pred).ravel()
        fail_rec = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        fail_prec = tn / (tn + fn) if (tn + fn) > 0 else 0.0
        fail_f1 = (2 * fail_prec * fail_rec) / (fail_prec + fail_rec) if (fail_prec + fail_rec) > 0 else 0.0
        if fail_f1 > best_f1_ab:
            best_f1_ab = fail_f1
            best_thresh_ab = th

    y_pred_optAB = (y_proba_optA1 >= best_thresh_ab).astype(int)
    optAB_metrics = evaluate_predictions(y_test, y_pred_optAB, y_proba_optA1)
    optAB_metrics["threshold"] = round(best_thresh_ab, 3)

    # Print Report
    print("=" * 75)
    print("EXPERIMENT RESULTS: CLASS IMBALANCE CORRECTION BENCHMARK")
    print("=" * 75)
    header = f"{'Metric':<28} | {'BEFORE (Base)':<13} | {'OPT A1 (GB Wt)':<14} | {'OPT A2 (RF Wt)':<14} | {'OPT B (Thresh)':<14} | {'OPT A+B (Combined)':<15}"
    print(header)
    print("-" * len(header))

    metrics_to_print = [
        ("Overall Accuracy", "accuracy", "%"),
        ("ROC-AUC Score", "roc_auc", ""),
        ("Failure Recall (Specificity)", "fail_recall", "%"),
        ("Failure Precision", "fail_precision", "%"),
        ("Failure F1 Score", "fail_f1", ""),
        ("Success Recall", "succ_recall", "%"),
        ("Success Precision", "succ_precision", "%"),
        ("Success F1 Score", "succ_f1", ""),
        ("Threshold Used", "threshold", "")
    ]

    for label, key, unit in metrics_to_print:
        val_base = f"{baseline_metrics.get(key, 0.5)}{unit}"
        val_a1 = f"{optA1_metrics.get(key, 0.5)}{unit}"
        val_a2 = f"{optA2_metrics.get(key, 0.5)}{unit}"
        val_b = f"{optB_metrics.get(key, 0.5)}{unit}"
        val_ab = f"{optAB_metrics.get(key, 0.5)}{unit}"
        print(f"{label:<28} | {val_base:<13} | {val_a1:<14} | {val_a2:<14} | {val_b:<14} | {val_ab:<15}")

    print("-" * len(header))
    print("Confusion Matrices [[TN, FP], [FN, TP]]:")
    print(f"  BEFORE (Baseline):         {baseline_metrics['confusion_matrix']}")
    print(f"  Option A1 (GB Sample Wt):  {optA1_metrics['confusion_matrix']}")
    print(f"  Option A2 (RF Class Wt):   {optA2_metrics['confusion_matrix']}")
    print(f"  Option B  (Thresh Tune):   {optB_metrics['confusion_matrix']} (thresh={best_thresh_b:.3f})")
    print(f"  Option A+B (Combined):     {optAB_metrics['confusion_matrix']} (thresh={best_thresh_ab:.3f})")

if __name__ == "__main__":
    run_experiments()
