"""
A/B Testing Harness for Smart Payment Advisor Recommendation Engine
===================================================================
Quantifies the real impact of the AI-driven recommendation engine (Group A)
against a naive uniform random control strategy (Group B) on identical simulated
checkout workloads using scipy.stats for defensible statistical analysis.

CRITICAL INTEGRITY PRINCIPLE:
Both Group A and Group B are evaluated against the EXACT SAME ground-truth
underlying probability model (EcosystemSimulator.calculate_transaction_probability).
No artificial bias or tuning is applied to favor Group A.
"""

import os
import sys
import argparse
import random
import json
import time
from datetime import datetime
import numpy as np

# SciPy for statistical tests
import scipy.stats as stats

# Matplotlib for visualization
try:
    import matplotlib
    matplotlib.use("Agg")  # Non-interactive backend
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

# Local backend modules
sys.path.insert(0, os.path.dirname(__file__))
from data_simulator import (
    EcosystemSimulator,
    weighted_choice,
    MERCHANT_WEIGHTS,
    DEVICE_WEIGHTS,
    METHOD_WEIGHTS,
    BANK_WEIGHTS,
    error_codes
)
from merchant_config import get_merchant_config, MERCHANT_CONFIGS
from recommendation_engine import get_recommendations


def evaluate_ground_truth_success(simulator, method, bank, hour, amount, now=None):
    """
    CRITICAL GROUND-TRUTH EVALUATION FUNCTION
    ----------------------------------------
    Given a chosen payment option (method, bank) and transaction context (hour, amount),
    calculates the true probability of transaction success using the multi-factor ecosystem
    model (drifting bank baselines, hourly rush patterns, maintenance windows, method limits,
    high-value fraud check cliffs, and rolling gateway load).

    This exact function is used to judge BOTH Group A (AI Routing) and Group B (Control).
    """
    prob, audit_factors, forced_error = simulator.calculate_transaction_probability(
        method=method,
        bank=bank,
        hour=hour,
        amount=amount,
        now=now
    )
    return prob, audit_factors, forced_error


class ABTestHarness:
    def __init__(self, num_samples=3000, seed=42, use_common_random_numbers=True):
        self.num_samples = num_samples
        self.seed = seed
        self.use_common_random_numbers = use_common_random_numbers
        self.simulator = EcosystemSimulator()
        self.results_A = []
        self.results_B = []
        self.events = []

    def run_simulation(self):
        """
        Executes N simulated checkout events.
        For each event:
          1. Samples realistic transaction context (merchant, amount, hour, day, device).
          2. Group A selects top payment option recommended by hybrid engine.
          3. Group B selects uniform random payment option from merchant's available methods.
          4. Evaluates both selections against the same ground-truth simulator.
        """
        if self.seed is not None:
            random.seed(self.seed)
            np.random.seed(self.seed)

        now_timestamp = time.time()

        for i in range(self.num_samples):
            # 1. Sample transaction context
            merchant_id = weighted_choice(MERCHANT_WEIGHTS)
            device = weighted_choice(DEVICE_WEIGHTS)
            hour = random.randint(0, 23)
            day_of_week = random.randint(0, 6)

            # Realistic amount distribution
            roll = random.random()
            if roll < 0.60:
                amount = round(random.uniform(100, 5000), 2)
            elif roll < 0.85:
                amount = round(random.uniform(5000, 45000), 2)
            else:
                amount = round(random.uniform(50000, 150000), 2)

            available_options = get_merchant_config(merchant_id)

            # 2. Group A Choice: AI Recommendation Engine
            recs = get_recommendations(
                merchant_id=merchant_id,
                amount=amount,
                device=device,
                available_methods_banks=available_options,
                hour=hour,
                day_of_week=day_of_week
            )
            top_rec = recs[0] if recs else None
            if top_rec:
                choice_A = (top_rec["method"], top_rec["bank"])
            else:
                choice_A = random.choice(available_options)

            # 3. Group B Choice: Baseline Uniform Random
            choice_B = random.choice(available_options)

            # 4. Ground-Truth Probability & Outcome Evaluation
            prob_A, factors_A, _ = evaluate_ground_truth_success(
                self.simulator, choice_A[0], choice_A[1], hour, amount, now_timestamp
            )
            prob_B, factors_B, _ = evaluate_ground_truth_success(
                self.simulator, choice_B[0], choice_B[1], hour, amount, now_timestamp
            )

            # Outcome sampling (Common Random Numbers for variance reduction)
            roll_outcome = random.random()
            if self.use_common_random_numbers:
                success_A = 1 if roll_outcome < prob_A else 0
                success_B = 1 if roll_outcome < prob_B else 0
            else:
                success_A = 1 if random.random() < prob_A else 0
                success_B = 1 if random.random() < prob_B else 0

            self.results_A.append(success_A)
            self.results_B.append(success_B)

            self.events.append({
                "id": i + 1,
                "merchant_id": merchant_id,
                "amount": amount,
                "hour": hour,
                "day_of_week": day_of_week,
                "device": device,
                "group_A_choice": choice_A,
                "group_A_prob": prob_A,
                "group_A_success": success_A,
                "group_B_choice": choice_B,
                "group_B_prob": prob_B,
                "group_B_success": success_B,
            })

    def analyze(self):
        """
        Calculates comprehensive statistical metrics using scipy.stats.
        Returns detailed summary dictionary.
        """
        N_A = len(self.results_A)
        N_B = len(self.results_B)

        succ_A = sum(self.results_A)
        succ_B = sum(self.results_B)

        rate_A = succ_A / N_A if N_A > 0 else 0.0
        rate_B = succ_B / N_B if N_B > 0 else 0.0

        abs_diff = (rate_A - rate_B) * 100.0  # Percentage points
        rel_improvement = ((rate_A - rate_B) / rate_B * 100.0) if rate_B > 0 else 0.0

        # Two-Proportion Z-Test (Hypothesis Test H0: pA = pB)
        p_pooled = (succ_A + succ_B) / (N_A + N_B)
        se_pooled = np.sqrt(p_pooled * (1.0 - p_pooled) * (1.0 / N_A + 1.0 / N_B))
        z_stat = (rate_A - rate_B) / se_pooled if se_pooled > 0 else 0.0
        p_value_z = 2.0 * stats.norm.sf(abs(z_stat))

        # Chi-Squared Test of Independence
        contingency_table = [[succ_A, N_A - succ_A], [succ_B, N_B - succ_B]]
        chi2_stat, p_value_chi2, dof, _ = stats.chi2_contingency(contingency_table)

        # 95% Confidence Interval for Difference in Proportions (pA - pB)
        se_diff = np.sqrt((rate_A * (1.0 - rate_A) / N_A) + (rate_B * (1.0 - rate_B) / N_B))
        z_critical = stats.norm.ppf(0.975)  # 1.95996 for 95% CI
        margin_error = z_critical * se_diff
        ci_lower = (rate_A - rate_B - margin_error) * 100.0
        ci_upper = (rate_A - rate_B + margin_error) * 100.0

        # Merchant Breakdown
        merchant_stats = {}
        for m in sorted(list(MERCHANT_CONFIGS.keys())):
            m_events = [e for e in self.events if e["merchant_id"] == m]
            m_N = len(m_events)
            if m_N > 0:
                m_succ_A = sum(e["group_A_success"] for e in m_events)
                m_succ_B = sum(e["group_B_success"] for e in m_events)
                m_rate_A = (m_succ_A / m_N) * 100.0
                m_rate_B = (m_succ_B / m_N) * 100.0
                m_abs_diff = m_rate_A - m_rate_B
                m_rel = ((m_rate_A - m_rate_B) / m_rate_B * 100.0) if m_rate_B > 0 else 0.0

                m_tbl = [[m_succ_A, m_N - m_succ_A], [m_succ_B, m_N - m_succ_B]]
                _, m_pval, _, _ = stats.chi2_contingency(m_tbl)

                merchant_stats[m] = {
                    "count": m_N,
                    "succ_A": m_succ_A,
                    "rate_A": round(m_rate_A, 2),
                    "succ_B": m_succ_B,
                    "rate_B": round(m_rate_B, 2),
                    "abs_diff": round(m_abs_diff, 2),
                    "rel_improvement": round(m_rel, 2),
                    "p_value": float(m_pval)
                }

        # Payment Method Breakdown (Selection Frequencies & Success Rates)
        method_stats = {}
        for method in ["Credit Card", "Debit Card", "Net Banking", "UPI", "Wallet"]:
            events_A_method = [e for e in self.events if e["group_A_choice"][0] == method]
            events_B_method = [e for e in self.events if e["group_B_choice"][0] == method]

            cnt_A = len(events_A_method)
            cnt_B = len(events_B_method)

            succ_A_m = sum(e["group_A_success"] for e in events_A_method) if cnt_A > 0 else 0
            succ_B_m = sum(e["group_B_success"] for e in events_B_method) if cnt_B > 0 else 0

            rate_A_m = (succ_A_m / cnt_A * 100.0) if cnt_A > 0 else 0.0
            rate_B_m = (succ_B_m / cnt_B * 100.0) if cnt_B > 0 else 0.0

            method_stats[method] = {
                "count_A": cnt_A,
                "pct_selected_A": round((cnt_A / N_A) * 100.0, 1),
                "succ_rate_A": round(rate_A_m, 2),
                "count_B": cnt_B,
                "pct_selected_B": round((cnt_B / N_B) * 100.0, 1),
                "succ_rate_B": round(rate_B_m, 2),
            }

        # Verdict Determination
        is_significant = p_value_z < 0.05
        if is_significant:
            if abs_diff > 0:
                verdict = f"STATISTICALLY SIGNIFICANT IMPROVEMENT (p = {p_value_z:.4e} < 0.05). AI Routing delivers a defensible +{abs_diff:.2f}% lift in success rate over Baseline Random."
            else:
                verdict = f"STATISTICALLY SIGNIFICANT REGRESSION (p = {p_value_z:.4e} < 0.05). AI Routing underperformed Baseline."
        else:
            verdict = f"NOT STATISTICALLY SIGNIFICANT (p = {p_value_z:.4f} >= 0.05). Insufficient evidence to reject null hypothesis."

        return {
            "num_samples": self.num_samples,
            "seed": self.seed,
            "group_A": {
                "label": "Group A (AI Routing)",
                "sample_size": N_A,
                "success_count": succ_A,
                "success_rate_pct": round(rate_A * 100.0, 2)
            },
            "group_B": {
                "label": "Group B (Baseline/Control)",
                "sample_size": N_B,
                "success_count": succ_B,
                "success_rate_pct": round(rate_B * 100.0, 2)
            },
            "metrics": {
                "abs_diff_pts": round(abs_diff, 2),
                "rel_improvement_pct": round(rel_improvement, 2),
                "z_statistic": round(float(z_stat), 4),
                "p_value_z": float(p_value_z),
                "chi2_statistic": round(float(chi2_stat), 4),
                "p_value_chi2": float(p_value_chi2),
                "ci_95_lower_pts": round(ci_lower, 2),
                "ci_95_upper_pts": round(ci_upper, 2),
                "is_statistically_significant": is_significant,
                "verdict": verdict
            },
            "merchant_breakdown": merchant_stats,
            "method_breakdown": method_stats
        }

    def print_report(self, summary):
        """Prints a comprehensive, portfolio-ready console report."""
        gA = summary["group_A"]
        gB = summary["group_B"]
        m = summary["metrics"]

        print("\n" + "=" * 80)
        print("         SMART PAYMENT ADVISOR - A/B TESTING & EXPERIMENTATION HARNESS")
        print("=" * 80)
        print(f"  Simulation Workload : {summary['num_samples']:,} Checkout Events")
        print(f"  Random Seed         : {summary['seed']}")
        print(f"  Evaluation Date     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 80)

        print("\n[1] OVERALL EXPERIMENT SUMMARY")
        print(f"  Group A (AI Routing)       : {gA['success_count']:,} / {gA['sample_size']:,} succeeded  ->  {gA['success_rate_pct']:.2f}%")
        print(f"  Group B (Baseline/Control) : {gB['success_count']:,} / {gB['sample_size']:,} succeeded  ->  {gB['success_rate_pct']:.2f}%")
        print("  " + "-" * 66)
        print(f"  Absolute Difference        : +{m['abs_diff_pts']:.2f} percentage points")
        print(f"  Relative Lift              : +{m['rel_improvement_pct']:.2f}% relative improvement")
        print(f"  95% Confidence Interval    : [{m['ci_95_lower_pts']:+.2f}%, {m['ci_95_upper_pts']:+.2f}%] points")
        print(f"  Two-Proportion Z-Statistic : {m['z_statistic']:.4f}")
        print(f"  P-Value (Z-test)           : {m['p_value_z']:.4e} ({'p < 0.01' if m['p_value_z'] < 0.01 else ('p < 0.05' if m['p_value_z'] < 0.05 else 'p >= 0.05')})")
        print(f"  Chi-Squared Statistic      : {m['chi2_statistic']:.4f} (p = {m['p_value_chi2']:.4e})")

        print("\n[2] VERDICT")
        print(f"  >> {m['verdict']}")

        print("\n[3] PER-MERCHANT BREAKDOWN")
        print(f"  {'Merchant':<22} | {'Tx Count':<8} | {'Group A %':<10} | {'Group B %':<10} | {'Abs Diff':<9} | {'Rel Lift':<9} | {'P-Value':<10}")
        print("  " + "-" * 92)
        for merch, stats_m in summary["merchant_breakdown"].items():
            print(f"  {merch:<22} | {stats_m['count']:<8} | {stats_m['rate_A']:<9.2f}% | {stats_m['rate_B']:<9.2f}% | {stats_m['abs_diff']:<+8.2f}% | {stats_m['rel_improvement']:<+8.2f}% | {stats_m['p_value']:<10.4e}")

        print("\n[4] PAYMENT METHOD SELECTION & ROUTING BEHAVIOR")
        print(f"  {'Method Category':<16} | {'Group A Choice %':<18} | {'Group A Success %':<18} | {'Group B Choice %':<18} | {'Group B Success %':<18}")
        print("  " + "-" * 98)
        for method, stats_meth in summary["method_breakdown"].items():
            print(f"  {method:<16} | {stats_meth['pct_selected_A']:<17.1f}% | {stats_meth['succ_rate_A']:<17.2f}% | {stats_meth['pct_selected_B']:<17.1f}% | {stats_meth['succ_rate_B']:<17.2f}%")

        print("\n[5] GROUND-TRUTH INTEGRITY NOTICE")
        print("  Both Group A and Group B were evaluated against the exact same ground-truth probability engine:")
        print("  `EcosystemSimulator.calculate_transaction_probability(method, bank, hour, amount)`")
        print("  No artificial advantage was granted to Group A. The difference is strictly due to intelligent routing.")
        print("=" * 80 + "\n")

    def plot_results(self, summary, output_path=None):
        """Generates matplotlib chart of results with error bars representing 95% CI."""
        if output_path is None:
            output_path = os.path.join(os.path.dirname(__file__), "ab_test_results.png")
        if not HAS_MATPLOTLIB:
            print("[INFO] Matplotlib not available; skipping chart generation.")
            return

        gA = summary["group_A"]
        gB = summary["group_B"]
        m = summary["metrics"]

        # 1. Overall bar chart data
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

        # Overall Comparison
        groups = ['Group A (AI Routing)', 'Group B (Baseline Control)']
        rates = [gA['success_rate_pct'], gB['success_rate_pct']]
        colors = ['#2e7d32', '#c62828']

        bars = ax1.bar(groups, rates, color=colors, width=0.5, edgecolor='black', alpha=0.85)
        ax1.set_ylabel('Success Rate (%)', fontsize=12, fontweight='bold')
        ax1.set_title('Overall Strategy Success Rate Comparison\n(with 95% Confidence Interval)', fontsize=13, fontweight='bold', pad=12)
        ax1.set_ylim(0, 100)
        ax1.grid(axis='y', linestyle='--', alpha=0.5)

        for bar in bars:
            height = bar.get_height()
            ax1.annotate(f'{height:.2f}%',
                         xy=(bar.get_x() + bar.get_width() / 2, height),
                         xytext=(0, 5),
                         textcoords="offset points",
                         ha='center', va='bottom', fontsize=11, fontweight='bold')

        # Add lift annotation
        ax1.text(0.5, 50, f"Lift: +{m['abs_diff_pts']:.2f}% pts\n(Rel: +{m['rel_improvement_pct']:.2f}%)\np = {m['p_value_z']:.4e}",
                 bbox=dict(boxstyle="round,pad=0.5", facecolor="#fff9c4", edgecolor="#fbc02d", alpha=0.9),
                 ha='center', fontsize=11, fontweight='bold')

        # Per-Merchant Comparison
        merchants = list(summary["merchant_breakdown"].keys())
        x = np.arange(len(merchants))
        width = 0.35

        rates_A_m = [summary["merchant_breakdown"][mch]["rate_A"] for mch in merchants]
        rates_B_m = [summary["merchant_breakdown"][mch]["rate_B"] for mch in merchants]

        rects1 = ax2.bar(x - width/2, rates_A_m, width, label='Group A (AI Routing)', color='#2e7d32', alpha=0.85)
        rects2 = ax2.bar(x + width/2, rates_B_m, width, label='Group B (Control)', color='#c62828', alpha=0.85)

        ax2.set_ylabel('Success Rate (%)', fontsize=12, fontweight='bold')
        ax2.set_title('Success Rate Comparison by Merchant Portal', fontsize=13, fontweight='bold', pad=12)
        ax2.set_xticks(x)
        ax2.set_xticklabels([mch.replace('_', ' ').title() for mch in merchants], fontsize=10)
        ax2.set_ylim(0, 100)
        ax2.legend(loc='lower right')
        ax2.grid(axis='y', linestyle='--', alpha=0.5)

        plt.tight_layout()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=300)
        plt.close()
        print(f"[SUCCESS] Matplotlib chart saved to: {output_path}")


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Smart Payment Advisor - A/B Testing Harness")
    parser.add_argument("--samples", type=int, default=3000, help="Number of simulated checkout events (default: 3000)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility (default: 42)")
    parser.add_argument("--no-plot", action="store_true", help="Disable matplotlib plot generation")
    parser.add_argument("--json", action="store_true", help="Output summary in JSON format")

    args = parser.parse_args()

    harness = ABTestHarness(num_samples=args.samples, seed=args.seed)
    harness.run_simulation()
    summary = harness.analyze()

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        harness.print_report(summary)

    if not args.no_plot and not args.json:
        harness.plot_results(summary)


if __name__ == "__main__":
    main()
