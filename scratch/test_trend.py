import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../backend')))

from recommendation_engine import get_recommendations
from database import init_db, inject_failure_spike

def test_in_memory_trend_cache():
    init_db()
    
    # 1. First call to recommendations
    recs1 = get_recommendations('college_fee_portal', 5000, 'Android', [('Net Banking', 'SBI'), ('Debit Card', 'SBI')])
    print("Call 1 recommendations:")
    for r in recs1:
        print(f"  {r['method']} ({r['bank']}): success_rate={r['success_rate']}%, trend={r['trend']}, rate_change={r['rate_change']}, prev_rate={r['previous_rate']}")
    
    # 2. Inject failure spike for Net Banking SBI
    print("\nInjecting failure spike for Net Banking SBI...")
    inject_failure_spike('college_fee_portal', 'Net Banking', 'SBI', 15)
    
    # 3. Second call to recommendations
    recs2 = get_recommendations('college_fee_portal', 5000, 'Android', [('Net Banking', 'SBI'), ('Debit Card', 'SBI')])
    print("\nCall 2 recommendations (after failure spike):")
    for r in recs2:
        print(f"  {r['method']} ({r['bank']}): success_rate={r['success_rate']}%, trend={r['trend']}, rate_change={r['rate_change']}, prev_rate={r['previous_rate']}")
        if r['method'] == 'Net Banking' and r['bank'] == 'SBI':
            assert r['trend'] == 'down', f"Expected trend 'down', got {r['trend']}"
            print("  SUCCESS: Trend correctly calculated as 'down' (↓) based on in-memory cache comparison!")

if __name__ == "__main__":
    test_in_memory_trend_cache()
